import type { ExtMessage } from "../../types/messages";
import fixWebmDuration from "fix-webm-duration";

const CHUNK_DURATION_MS = 30000;
const FINAL_CHUNK_DURATION_MS = 250;
const LEVEL_INTERVAL_MS = 300;

let audioContext: AudioContext | null = null;
let tabStream: MediaStream | null = null;
let micStream: MediaStream | null = null;
let mixedStream: MediaStream | null = null;
let currentRecorder: MediaRecorder | null = null;
let analyser: AnalyserNode | null = null;
let levelInterval: number | null = null;
let loopPromise: Promise<void> | null = null;
let running = false;
let paused = false;
let stopping = false;
let finalSent = false;
let currentMeetingId: string | null = null;
let currentMimeType = "audio/webm";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!isOffscreenMessage(msg)) return false;

  handleMessage(msg)
    .then(sendResponse)
    .catch((e: unknown) => {
      chrome.runtime
        .sendMessage({
          type: "RECORDING_ERROR",
          error: e instanceof Error ? e.message : String(e),
        } satisfies ExtMessage)
        .catch(() => {});
      sendResponse({ error: String(e) });
    });
  return true;
});

async function handleMessage(msg: ExtMessage) {
  switch (msg.type) {
    case "OFFSCREEN_START":
      await startCapture(msg.streamId, msg.meetingId, msg.micDeviceId);
      return { ok: true };

    case "OFFSCREEN_PAUSE":
      pauseCapture();
      return { ok: true };

    case "OFFSCREEN_RESUME":
      await resumeCapture();
      return { ok: true };

    case "OFFSCREEN_STOP":
      await stopCapture();
      return { ok: true };

    case "OFFSCREEN_TOGGLE_MIC":
      toggleMic();
      return { ok: true };

    case "OFFSCREEN_TEST_AUDIO":
      return await captureTestAudio();
  }
}

async function startCapture(
  streamId: string,
  meetingId: string,
  micDeviceId?: string,
) {
  await stopCapture();

  currentMeetingId = meetingId;
  currentMimeType = resolveMimeType();
  audioContext = new AudioContext();

  // Resume immediately before any source connections — new AudioContexts start
  // suspended in extension contexts and must be explicitly resumed.
  if (audioContext.state === "suspended") {
    await audioContext.resume();
  }

  const destination = audioContext.createMediaStreamDestination();

  analyser = audioContext.createAnalyser();
  analyser.fftSize = 256;

  // AnalyserNode needs a downstream connection to stay active in Chrome's audio graph
  // (nodes with no path to the destination may be de-activated). Route through a
  // silent gain node into destination so the analyser is always in the pull chain.
  const analyserSink = audioContext.createGain();
  analyserSink.gain.value = 0;
  analyser.connect(analyserSink);
  analyserSink.connect(destination);

  // Silent oscillator keeps the AudioContext from auto-suspending between chunks.
  try {
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    gainNode.gain.value = 0;
    oscillator.connect(gainNode);
    gainNode.connect(destination);
    gainNode.connect(audioContext.destination); // hardware path keeps Chrome from suspending
    oscillator.start();
  } catch (oscErr) {
    console.warn("[offscreen] Failed to start silent oscillator:", oscErr);
  }

  tabStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: { chromeMediaSource: "tab", chromeMediaSourceId: streamId },
    } as unknown as MediaTrackConstraints,
    video: false,
  });

  const tabTracks = tabStream.getAudioTracks();
  console.log(
    "[offscreen] Tab audio tracks:",
    tabTracks.map((t) => ({
      readyState: t.readyState,
      muted: t.muted,
      enabled: t.enabled,
      label: t.label,
    })),
  );
  console.log("[offscreen] Tab track settings:", tabTracks[0]?.getSettings());

  if (
    tabTracks.length === 0 ||
    tabTracks.every((t) => t.readyState === "ended")
  ) {
    console.error(
      "[offscreen] Tab capture returned no live tracks — stream ID may have expired",
    );
  }

  const tabSource = audioContext.createMediaStreamSource(tabStream);
  tabSource.connect(destination);
  tabSource.connect(analyser);
  // Route tab audio to hardware output so the user hears the tab during recording,
  // and so the AudioContext has a real hardware sink that prevents auto-suspend.
  tabSource.connect(audioContext.destination);

  try {
    const audioConstraints: MediaTrackConstraints = micDeviceId
      ? { deviceId: { exact: micDeviceId } }
      : {};
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: audioConstraints,
      video: false,
    });
    const micTracks = micStream.getAudioTracks();
    console.log(
      "[offscreen] Mic audio tracks:",
      micTracks.map((t) => ({
        readyState: t.readyState,
        muted: t.muted,
        enabled: t.enabled,
        label: t.label,
      })),
    );
    console.log("[offscreen] Mic track settings:", micTracks[0]?.getSettings());
    const micSource = audioContext.createMediaStreamSource(micStream);
    micSource.connect(destination);
    micSource.connect(analyser);
  } catch (micErr) {
    console.warn("[offscreen] Failed to capture microphone:", micErr);
    micStream = null;
  }

  mixedStream = destination.stream;
  running = true;
  paused = false;
  stopping = false;
  finalSent = false;

  startLevelReporting();

  loopPromise = runChunkLoop();
}

function startLevelReporting() {
  if (levelInterval !== null) window.clearInterval(levelInterval);
  const buf = new Uint8Array(analyser?.frequencyBinCount ?? 128);
  levelInterval = window.setInterval(() => {
    if (!analyser || !running) return;
    analyser.getByteFrequencyData(buf);
    const sum = buf.reduce((a, b) => a + b, 0);
    const level = Math.round((sum / buf.length / 255) * 100);
    console.log(
      `[offscreen] ctx=${audioContext?.state ?? "null"} level=${level}`,
    );
    chrome.runtime
      .sendMessage({ type: "AUDIO_LEVEL", level } satisfies ExtMessage)
      .catch(() => {});
  }, LEVEL_INTERVAL_MS);
}

function stopLevelReporting() {
  if (levelInterval !== null) {
    window.clearInterval(levelInterval);
    levelInterval = null;
  }
}

function pauseCapture() {
  paused = true;
  stopCurrentRecorder();
}

async function resumeCapture() {
  paused = false;
  if (audioContext && audioContext.state === "suspended") {
    await audioContext.resume();
  }
}

async function stopCapture() {
  if (!running && !mixedStream) return;

  stopping = true;
  paused = false;
  running = false;
  stopLevelReporting();
  stopCurrentRecorder();
  await loopPromise;

  if (!finalSent && mixedStream && currentMeetingId) {
    const finalBlob = await recordSingleChunk(FINAL_CHUNK_DURATION_MS);
    if (finalBlob.size > 0) {
      await sendAudioChunk(finalBlob, true);
      finalSent = true;
    }
  }

  tabStream?.getTracks().forEach((track) => track.stop());
  micStream?.getTracks().forEach((track) => track.stop());
  await audioContext?.close();

  audioContext = null;
  tabStream = null;
  micStream = null;
  mixedStream = null;
  analyser = null;
  currentRecorder = null;
  loopPromise = null;
  currentMeetingId = null;
  stopping = false;
  paused = false;
}

async function runChunkLoop() {
  while (running || currentRecorder) {
    if (!currentMeetingId) break;
    if (paused) {
      await sleep(200);
      continue;
    }

    const blob = await recordSingleChunk(CHUNK_DURATION_MS);
    console.log(
      `[offscreen] Chunk recorded: ${blob.size} bytes, type: ${blob.type}`,
    );
    if (blob.size > 0) {
      const isFinal = stopping || !running;
      await sendAudioChunk(blob, isFinal);
      finalSent = isFinal;
    }
  }
}

async function recordSingleChunk(durationMs: number): Promise<Blob> {
  if (!mixedStream) {
    return new Blob([], { type: currentMimeType });
  }

  if (audioContext && audioContext.state !== "running") {
    console.warn(
      `[offscreen] AudioContext is '${audioContext.state}' before chunk — resuming`,
    );
    await audioContext.resume();
    if (audioContext.state !== "running") {
      console.error(
        "[offscreen] AudioContext failed to resume — chunk will be silent",
      );
      chrome.runtime
        .sendMessage({
          type: "RECORDING_ERROR",
          error: `AudioContext stuck in '${audioContext.state}' — audio may be silent`,
        } satisfies ExtMessage)
        .catch(() => {});
    }
  }

  return new Promise<Blob>((resolve, reject) => {
    const chunks: Blob[] = [];
    const recorder = new MediaRecorder(mixedStream!, {
      mimeType: currentMimeType,
      audioBitsPerSecond: 128_000,
    });
    currentRecorder = recorder;

    const timeout = window.setTimeout(() => stopRecorder(recorder), durationMs);
    const startTime = Date.now();

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data);
    };
    recorder.onerror = () => {
      window.clearTimeout(timeout);
      reject(new Error("MediaRecorder failed while recording audio chunk"));
    };
    recorder.onstop = () => {
      window.clearTimeout(timeout);
      if (currentRecorder === recorder) currentRecorder = null;
      const actualDurationMs = Date.now() - startTime;
      const blob = new Blob(chunks, { type: currentMimeType });
      fixWebmDuration(blob, actualDurationMs, { logger: false })
        .then(resolve)
        .catch(() => resolve(blob));
    };

    // timeslice ensures ondataavailable fires periodically, not only on stop
    recorder.start(5_000);
  });
}

async function captureTestAudio(): Promise<{
  bytes?: number[];
  contentType?: string;
  error?: string;
}> {
  if (!mixedStream || !running) {
    return {
      error: "Нет активной записи. Запустите запись, затем нажмите тест.",
    };
  }

  const testChunks: Blob[] = [];
  const testRecorder = new MediaRecorder(mixedStream, {
    mimeType: currentMimeType,
    audioBitsPerSecond: 64_000,
  });

  await new Promise<void>((resolve) => {
    testRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) testChunks.push(e.data);
    };
    testRecorder.onstop = () => resolve();
    testRecorder.start(1_000);
    window.setTimeout(() => {
      if (testRecorder.state === "recording") testRecorder.stop();
    }, 5_000);
  });

  const blob = new Blob(testChunks, { type: currentMimeType });
  console.log(`[offscreen] Test audio: ${blob.size} bytes`);
  const buffer = await blob.arrayBuffer();
  return { bytes: Array.from(new Uint8Array(buffer)), contentType: blob.type };
}

async function sendAudioChunk(blob: Blob, finalChunk: boolean) {
  if (!currentMeetingId) return;
  const buffer = await blob.arrayBuffer();
  const chunk = Array.from(new Uint8Array(buffer));
  await chrome.runtime.sendMessage({
    type: "AUDIO_CHUNK",
    chunk,
    meetingId: currentMeetingId,
    contentType: blob.type || currentMimeType,
    finalChunk,
  } satisfies ExtMessage);
}

function toggleMic() {
  micStream?.getAudioTracks().forEach((track) => {
    track.enabled = !track.enabled;
  });
}

function resolveMimeType(): string {
  if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
    return "audio/webm;codecs=opus";
  }
  if (MediaRecorder.isTypeSupported("audio/webm")) {
    return "audio/webm";
  }
  throw new Error("MediaRecorder не поддерживает audio/webm");
}

function stopCurrentRecorder() {
  stopRecorder(currentRecorder);
}

function stopRecorder(recorder: MediaRecorder | null) {
  if (recorder && recorder.state === "recording") {
    recorder.stop();
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function isOffscreenMessage(msg: unknown): msg is ExtMessage {
  if (typeof msg !== "object" || msg === null || !("type" in msg)) return false;
  return [
    "OFFSCREEN_START",
    "OFFSCREEN_PAUSE",
    "OFFSCREEN_RESUME",
    "OFFSCREEN_STOP",
    "OFFSCREEN_TOGGLE_MIC",
    "OFFSCREEN_TEST_AUDIO",
  ].includes(String((msg as { type?: unknown }).type));
}
