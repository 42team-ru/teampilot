from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger

from chunk_sender import send_chunk
from config import settings


@dataclass
class TelemostSession:
    meeting_id: str
    meeting_url: str
    team_id: str
    sink_name: str
    sink_module_id: str
    mic_sink_name: str
    mic_module_id: str
    _chunk_index: int = 0
    _stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    _tasks: list[asyncio.Task] = field(default_factory=list)


_sessions: dict[str, TelemostSession] = {}


async def start_session(meeting_id: str, meeting_url: str, team_id: str = "") -> None:
    """Start a new Playwright + audio recording session for the given meeting."""
    if meeting_id in _sessions:
        logger.warning("Telemost session already active: meeting_id={}", meeting_id)
        return

    short_id = meeting_id.replace("-", "")[:12]
    sink_name = f"bot_sink_{short_id}"
    sink_module_id = _create_virtual_sink(sink_name, "TeamPilotBot")
    if sink_module_id is None:
        raise RuntimeError(f"Failed to create PulseAudio virtual sink {sink_name!r}")

    # Virtual microphone: a second null-sink whose .monitor is fed to Chrome as the
    # input device (PULSE_SOURCE). Nothing writes to it by default → silence, so the
    # bot no longer transmits Chrome's fake-device beep. TTS can later play into this
    # sink to make the bot "speak" in the call.
    mic_sink_name = f"bot_mic_{short_id}"
    mic_module_id = _create_virtual_sink(mic_sink_name, "TeamPilotBotMic")
    if mic_module_id is None:
        _remove_virtual_sink(sink_module_id)
        raise RuntimeError(f"Failed to create PulseAudio virtual mic sink {mic_sink_name!r}")

    session = TelemostSession(
        meeting_id=meeting_id,
        meeting_url=meeting_url,
        team_id=team_id,
        sink_name=sink_name,
        sink_module_id=sink_module_id,
        mic_sink_name=mic_sink_name,
        mic_module_id=mic_module_id,
    )
    _sessions[meeting_id] = session

    session._tasks.append(asyncio.create_task(_browser_task(session)))
    session._tasks.append(asyncio.create_task(_record_loop(session)))
    logger.info("Telemost session started: meeting_id={} sink={}", meeting_id, sink_name)


async def stop_session(meeting_id: str) -> None:
    """Stop and clean up the session for the given meeting."""
    session = _sessions.pop(meeting_id, None)
    if session is None:
        return

    session._stop_event.set()
    for task in session._tasks:
        task.cancel()
    await asyncio.gather(*session._tasks, return_exceptions=True)

    _remove_virtual_sink(session.sink_module_id)
    _remove_virtual_sink(session.mic_module_id)
    logger.info("Telemost session stopped: meeting_id={}", meeting_id)


def is_active(meeting_id: str) -> bool:
    return meeting_id in _sessions


async def _browser_task(session: TelemostSession) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("playwright not installed — run: uv add playwright && playwright install chromium")
        return

    # Derive a stable display number from the meeting_id to avoid collisions
    display_num = 100 + (int(session.meeting_id.replace("-", "")[:4], 16) % 100)
    display = f":{display_num}"

    xvfb_proc: subprocess.Popen | None = None
    use_headless = False
    try:
        xvfb_proc = subprocess.Popen(
            ["Xvfb", display, "-screen", "0", "1280x720x24"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("Xvfb started: display={} pid={}", display, xvfb_proc.pid)
    except FileNotFoundError:
        logger.warning("Xvfb not found — falling back to headless=True (Chrome audio may not route to PulseAudio)")
        use_headless = True

    # PULSE_SINK: where Chrome plays the call audio (we capture its .monitor).
    # PULSE_SOURCE: the bot's microphone — our silent virtual mic sink's monitor.
    env = {
        **os.environ,
        "PULSE_SINK": session.sink_name,
        "PULSE_SOURCE": f"{session.mic_sink_name}.monitor",
    }
    if not use_headless:
        env["DISPLAY"] = display

    try:
        async with async_playwright() as p:
            import shutil
            chrome_path = (
                shutil.which("google-chrome")
                or shutil.which("chromium-browser")
                or shutil.which("chromium")
            )
            browser = await p.chromium.launch(
                headless=use_headless,
                executable_path=chrome_path or None,
                args=[
                    # Auto-grant mic/camera prompts. We intentionally do NOT pass
                    # --use-fake-device-for-media-stream: its fake audio device emits a
                    # periodic ~1kHz beep that would be broadcast to all participants.
                    # Instead Chrome uses our silent virtual mic via PULSE_SOURCE.
                    "--use-fake-ui-for-media-stream",
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
                env=env,
            )
            context = await browser.new_context(
                permissions=["microphone", "camera"],
            )
            page = await context.new_page()

            logger.info("Playwright: navigating to {}", session.meeting_url)
            await page.goto(session.meeting_url, wait_until="domcontentloaded")

            try:
                join_btn = page.locator('[data-testid="enter-conference-button"]')
                await join_btn.wait_for(timeout=20_000)
                await join_btn.click()
                logger.info("Playwright: joined Telemost call meeting_id={}", session.meeting_id)
                # Don't block — reroute runs in background while call is active
                asyncio.create_task(_reroute_chrome_audio(session.sink_name))
            except Exception as e:
                logger.error("Playwright: failed to click join button: {}", e)
                await browser.close()
                return

            await session._stop_event.wait()
            await browser.close()
            logger.info("Playwright: browser closed meeting_id={}", session.meeting_id)
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb_proc.kill()
            logger.info("Xvfb terminated: display={}", display)


async def _record_loop(session: TelemostSession) -> None:
    # Give the browser time to join the call
    await asyncio.sleep(5)

    monitor_source = f"{session.sink_name}.monitor"
    logger.info("Audio recorder started: source={}", monitor_source)

    while not session._stop_event.is_set():
        try:
            audio_bytes = await _capture_chunk(monitor_source, settings.CHUNK_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Audio capture error: {}", e)
            await asyncio.sleep(2)
            continue

        if not audio_bytes:
            continue

        chunk_index = session._chunk_index
        session._chunk_index += 1

        if settings.CHUNKS_DEBUG_DIR:
            import pathlib
            debug_dir = pathlib.Path(settings.CHUNKS_DEBUG_DIR) / session.meeting_id
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_path = debug_dir / f"chunk-{chunk_index:06d}.wav"
            debug_path.write_bytes(audio_bytes)
            logger.debug("Chunk saved locally: {}", debug_path)

        try:
            await send_chunk(
                meeting_id=session.meeting_id,
                team_id=session.team_id,
                chunk_index=chunk_index,
                audio_bytes=audio_bytes,
                content_type="audio/wav",
                original_filename=f"chunk-{chunk_index:06d}.wav",
                final_chunk=False,
            )
        except Exception as e:
            logger.error(
                "Chunk upload failed: meeting_id={} index={}: {}",
                session.meeting_id, chunk_index, e,
            )

    # Send final chunk to signal end of recording
    try:
        await send_chunk(
            meeting_id=session.meeting_id,
            team_id=session.team_id,
            chunk_index=session._chunk_index,
            audio_bytes=b"",
            content_type="audio/wav",
            original_filename=f"chunk-{session._chunk_index:06d}.wav",
            final_chunk=True,
        )
    except Exception:
        pass
    logger.info("Audio recorder stopped: meeting_id={}", session.meeting_id)


async def _capture_chunk(source: str, duration: int) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name

    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y",
            "-f", "pulse", "-i", source,
            "-t", str(duration),
            "-ar", str(settings.SAMPLE_RATE),
            "-ac", "1",
            "-f", "wav",
            tmp_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _parse_chrome_sink_input(pactl_output: str) -> int | None:
    """Parse 'pactl list sink-inputs' output and return Chrome's sink-input ID."""
    current_id: int | None = None
    chrome_keywords = ("google-chrome", "chromium", "chrome")

    for line in pactl_output.splitlines():
        line = line.strip()
        if line.startswith("Sink Input #"):
            try:
                current_id = int(line.split("#")[1])
            except (IndexError, ValueError):
                current_id = None
        elif current_id is not None and any(kw in line.lower() for kw in chrome_keywords):
            return current_id
    return None


async def _reroute_chrome_audio(sink_name: str) -> bool:
    """Find Chrome's PulseAudio sink-input and move it to our virtual sink.
    Polls for up to 20 seconds (10 attempts × 2s).
    """
    for attempt in range(10):
        await asyncio.sleep(2)
        try:
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"],
                capture_output=True, text=True, timeout=5,
            )
        except Exception as e:
            logger.warning("pactl list sink-inputs failed: {}", e)
            continue

        sink_input_id = _parse_chrome_sink_input(result.stdout)
        if sink_input_id is not None:
            move = subprocess.run(
                ["pactl", "move-sink-input", str(sink_input_id), sink_name],
                capture_output=True, text=True, timeout=5,
            )
            if move.returncode == 0:
                logger.info("Chrome audio rerouted: sink-input={} → sink={}", sink_input_id, sink_name)
                return True
            else:
                logger.warning("move-sink-input failed: {}", move.stderr.strip())
        else:
            logger.debug("Chrome sink-input not found yet (attempt {})", attempt + 1)
    logger.error("Failed to reroute Chrome audio after 10 attempts")
    return False


def _create_virtual_sink(sink_name: str, description: str = "TeamPilotBot") -> Optional[str]:
    try:
        result = subprocess.run(
            [
                "pactl", "load-module", "module-null-sink",
                f"sink_name={sink_name}",
                f"sink_properties=device.description={description}",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        logger.error("pactl failed: {}", result.stderr)
        return None
    except Exception as e:
        logger.error("Failed to create PulseAudio sink: {}", e)
        return None


def _remove_virtual_sink(module_id: str) -> None:
    try:
        subprocess.run(["pactl", "unload-module", module_id], timeout=5, check=False)
    except Exception as e:
        logger.warning("Failed to unload PulseAudio module {}: {}", module_id, e)
