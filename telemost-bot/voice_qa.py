"""Голосовой Q&A в звонке: always-listen + STT + триггер «Пилот».

Слушает речь участников (монитор capture-sink), режет на фразы (webrtcvad),
распознаёт каждую фразу (Groq Whisper). Если в тексте есть wake-слово —
отправляет вопрос в llm-worker (/voice/answer) и проигрывает ответный звук в
виртуальный микрофон (mic-sink), так что его слышат все в звонке.

STT живёт здесь намеренно: при always-listen бот всё равно читает каждую фразу,
и это же распознавание уже содержит сам вопрос — второй STT не нужен.
"""
from __future__ import annotations

import asyncio
import io
import wave
from collections import deque
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from config import settings

if TYPE_CHECKING:
    from session_manager import TelemostSession

_SAMPLE_RATE = 16000
_FRAME_MS = 20
_FRAME_BYTES = int(_SAMPLE_RATE * _FRAME_MS / 1000) * 2  # 16-bit mono → 640 байт/20мс


def _wake_words() -> list[str]:
    return [w.strip().lower() for w in settings.WAKE_WORDS.split(",") if w.strip()]


def _extract_question(text: str) -> str | None:
    """Если в тексте есть wake-слово — вернуть часть после него (сам вопрос)."""
    low = text.lower()
    best = None
    for w in _wake_words():
        idx = low.find(w)
        if idx != -1 and (best is None or idx < best[0]):
            best = (idx, w)
    if best is None:
        return None
    idx, w = best
    question = text[idx + len(w):].lstrip(" ,.!?:;—-\t").strip()
    return question


def _pcm_to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


async def _transcribe(pcm: bytes) -> str:
    """Groq Whisper (OpenAI-совместимый /audio/transcriptions), response_format=text."""
    wav = _pcm_to_wav(pcm)
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(
            f"{settings.WHISPER_API_BASE.rstrip('/')}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.WHISPER_API_KEY}"},
            files={"file": ("utterance.wav", wav, "audio/wav")},
            data={
                "model": settings.WHISPER_MODEL,
                "language": settings.WHISPER_LANGUAGE,
                "response_format": "text",
                "temperature": "0",
            },
        )
        resp.raise_for_status()
        return resp.text.strip()


async def _ask_worker(question: str, team_id: str, meeting_id: str) -> bytes:
    """POST вопрос в llm-worker, получить аудио-ответ (mp3)."""
    async with httpx.AsyncClient(timeout=settings.VOICE_REPLY_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            f"{settings.WORKER_URL.rstrip('/')}/voice/answer",
            json={"text": question, "team_id": team_id, "meeting_id": meeting_id},
        )
        resp.raise_for_status()
        return resp.content


async def _play_to_mic(audio: bytes, mic_sink: str) -> None:
    """Проиграть mp3-ответ в mic-sink через ffmpeg → PulseAudio."""
    # -re: отдавать в realtime. PipeWire null-sink не throttle'ит продюсера по
    # часам сcsink'а — без -re ffmpeg «выстреливает» весь звук пачкой за доли
    # секунды, и Chrome успевает захватить с монитора только огрызок («пфф»).
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-re", "-i", "pipe:0",
        "-ac", "2", "-ar", "48000",
        "-f", "pulse", "-device", mic_sink, "TeamPilotVoice",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate(input=audio)


async def _handle_utterance(
    session: "TelemostSession", pcm: bytes, busy: asyncio.Event
) -> None:
    busy.set()
    try:
        text = await _transcribe(pcm)
        if not text:
            return
        question = _extract_question(text)
        if question is None:
            logger.debug("voice: фраза без триггера: {!r}", text)
            return
        if len(question) < 3:
            logger.info("voice: триггер без вопроса ({!r}) — пропуск", text)
            return

        logger.info("voice: вопрос Пилоту: {!r}", question)
        audio = await _ask_worker(question, session.team_id, session.meeting_id)
        await _play_to_mic(audio, session.mic_sink_name)
        logger.info("voice: ответ проигран в звонок ({} байт)", len(audio))
        # небольшой хвост, чтобы не словить эхо собственного ответа
        await asyncio.sleep(0.5)
    except Exception as e:  # noqa: BLE001 — звонок важнее одной осечки
        logger.opt(exception=True).warning("voice: ошибка обработки вопроса: {}", e)
    finally:
        busy.clear()


async def run_voice_qa(session: "TelemostSession") -> None:
    """Главный таск: непрерывный захват + VAD + диспетчеризация вопросов."""
    if not settings.VOICE_QA_ENABLED:
        return
    if settings.WAKE_MODE.lower() == "openwakeword":
        await run_voice_qa_oww(session)
        return
    if not settings.WHISPER_API_KEY:
        logger.warning("voice: WHISPER_API_KEY пуст — голосовой Q&A отключён")
        return
    try:
        import webrtcvad
    except ImportError:
        logger.error("voice: webrtcvad не установлен — `uv add webrtcvad`")
        return

    # Дать браузеру зайти в звонок и заработать роутингу аудио
    await asyncio.sleep(8)

    source = f"{session.sink_name}.monitor"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "pulse", "-i", source,
        "-ar", str(_SAMPLE_RATE), "-ac", "1", "-f", "s16le", "pipe:1",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    logger.info("voice: слушаю звонок source={} (триггеры: {})", source, _wake_words())

    vad = webrtcvad.Vad(settings.VAD_AGGRESSIVENESS)
    busy = asyncio.Event()  # set, пока обрабатываем/отвечаем — новые фразы игнорим

    prebuffer: deque[bytes] = deque(maxlen=15)  # ~300мс до начала речи
    voiced: list[bytes] = []
    in_speech = False
    silence_frames = 0

    silence_limit = max(1, settings.VAD_SILENCE_MS // _FRAME_MS)
    min_frames = max(1, settings.MIN_UTTERANCE_MS // _FRAME_MS)
    max_frames = max(min_frames + 1, settings.MAX_UTTERANCE_MS // _FRAME_MS)

    def reset() -> None:
        nonlocal in_speech, silence_frames, voiced
        in_speech = False
        silence_frames = 0
        voiced = []

    try:
        while not session._stop_event.is_set():
            try:
                frame = await proc.stdout.readexactly(_FRAME_BYTES)
            except asyncio.IncompleteReadError:
                break

            # Пока отвечаем — дренируем поток, но не детектим (анти-эхо/без перекрытий)
            if busy.is_set():
                if in_speech:
                    reset()
                continue

            try:
                is_speech = vad.is_speech(frame, _SAMPLE_RATE)
            except Exception:
                continue

            if not in_speech:
                prebuffer.append(frame)
                if is_speech:
                    in_speech = True
                    voiced = list(prebuffer)
                    silence_frames = 0
            else:
                voiced.append(frame)
                if is_speech:
                    silence_frames = 0
                else:
                    silence_frames += 1

                end = silence_frames >= silence_limit
                too_long = len(voiced) >= max_frames
                if end or too_long:
                    utterance = voiced
                    speech_len = len(utterance) - silence_frames
                    reset()
                    prebuffer.clear()
                    if speech_len >= min_frames:
                        pcm = b"".join(utterance)
                        asyncio.create_task(_handle_utterance(session, pcm, busy))
    finally:
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=3)
        except Exception:
            proc.kill()
        logger.info("voice: слушатель остановлен meeting_id={}", session.meeting_id)


# ── Режим openWakeWord (локальный wake-word, без STT на каждую фразу) ──────────
async def _answer_from_pcm(session: "TelemostSession", pcm: bytes) -> None:
    """Распознать вопрос (один STT) и ответить голосом в звонок."""
    text = (await _transcribe(pcm)).strip()
    if len(text) < 2:
        return
    logger.info("voice(oww): вопрос: {!r}", text)
    audio = await _ask_worker(text, session.team_id, session.meeting_id)
    await _play_to_mic(audio, session.mic_sink_name)
    await asyncio.sleep(0.5)  # хвост против эха


async def _record_question(stdout, vad) -> bytes:
    """После триггера пишем фразу до тишины (VAD). 20мс-кадры."""
    sil_limit = max(1, settings.VAD_SILENCE_MS // _FRAME_MS)
    max_frames = max(2, settings.MAX_UTTERANCE_MS // _FRAME_MS)
    start_budget = 1500 // _FRAME_MS  # ждём начала речи до 1.5с после wake
    frames: list[bytes] = []
    started = False
    silence = 0
    while True:
        try:
            frame = await stdout.readexactly(_FRAME_BYTES)
        except asyncio.IncompleteReadError:
            break
        speech = vad.is_speech(frame, _SAMPLE_RATE)
        if not started:
            if speech:
                started = True
                frames.append(frame)
            else:
                start_budget -= 1
                if start_budget <= 0:
                    return b""
            continue
        frames.append(frame)
        silence = 0 if speech else silence + 1
        if silence >= sil_limit or len(frames) >= max_frames:
            break
    return b"".join(frames)


async def run_voice_qa_oww(session: "TelemostSession") -> None:
    """Wake-word через openWakeWord: триггер локально → запись вопроса → один STT → воркер."""
    if not settings.WHISPER_API_KEY:
        logger.warning("voice(oww): WHISPER_API_KEY пуст — нечем распознать вопрос")
        return
    try:
        import numpy as np
        import webrtcvad
        from openwakeword.model import Model as OWWModel
    except ImportError as e:
        logger.error("voice(oww): нет зависимостей ({}) — `uv add openwakeword`", e)
        return

    try:
        kwargs = {"inference_framework": settings.OWW_INFERENCE_FRAMEWORK}
        if settings.OWW_MODEL_PATH:
            kwargs["wakeword_models"] = [settings.OWW_MODEL_PATH]
        try:
            oww = OWWModel(**kwargs)
        except Exception:
            import openwakeword.utils
            openwakeword.utils.download_models()
            oww = OWWModel(**kwargs)
    except Exception as e:  # noqa: BLE001
        logger.error("voice(oww): не удалось загрузить модель ({}) — режим отключён", e)
        return

    await asyncio.sleep(8)
    source = f"{session.sink_name}.monitor"
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "pulse", "-i", source,
        "-ar", str(_SAMPLE_RATE), "-ac", "1", "-f", "s16le", "pipe:1",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    vad = webrtcvad.Vad(settings.VAD_AGGRESSIVENESS)
    oww_bytes = 1280 * 2  # 80мс кадр для openWakeWord
    model_label = settings.OWW_MODEL_PATH or "встроенные"
    logger.info("voice(oww): слушаю звонок (модель: {}, порог {})", model_label, settings.OWW_THRESHOLD)

    try:
        while not session._stop_event.is_set():
            try:
                chunk = await proc.stdout.readexactly(oww_bytes)
            except asyncio.IncompleteReadError:
                break
            scores = oww.predict(np.frombuffer(chunk, dtype=np.int16))
            if scores and max(scores.values()) >= settings.OWW_THRESHOLD:
                logger.info("voice(oww): триггер! ({:.2f})", max(scores.values()))
                pcm = await _record_question(proc.stdout, vad)
                if pcm:
                    try:
                        await _answer_from_pcm(session, pcm)
                    except Exception as e:  # noqa: BLE001
                        logger.opt(exception=True).warning("voice(oww): ошибка ответа: {}", e)
                oww.reset()
    finally:
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=3)
        except Exception:
            proc.kill()
        logger.info("voice(oww): слушатель остановлен meeting_id={}", session.meeting_id)
