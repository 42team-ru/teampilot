import type { ExtMessage } from '../../types/messages'

const CHUNK_DURATION_MS = 15000
const FINAL_CHUNK_DURATION_MS = 250

let audioContext: AudioContext | null = null
let tabStream: MediaStream | null = null
let micStream: MediaStream | null = null
let mixedStream: MediaStream | null = null
let currentRecorder: MediaRecorder | null = null
let loopPromise: Promise<void> | null = null
let running = false
let paused = false
let stopping = false
let finalSent = false
let currentMeetingId: string | null = null
let currentMimeType = 'audio/webm'

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (!isOffscreenMessage(msg)) return false

  handleMessage(msg).then(sendResponse).catch((e: unknown) => {
    chrome.runtime.sendMessage({
      type: 'RECORDING_ERROR',
      error: e instanceof Error ? e.message : String(e),
    } satisfies ExtMessage).catch(() => {})
    sendResponse({ error: String(e) })
  })
  return true
})

async function handleMessage(msg: ExtMessage) {
  switch (msg.type) {
    case 'OFFSCREEN_START':
      await startCapture(msg.streamId, msg.meetingId, msg.micDeviceId)
      return { ok: true }

    case 'OFFSCREEN_PAUSE':
      pauseCapture()
      return { ok: true }

    case 'OFFSCREEN_RESUME':
      resumeCapture()
      return { ok: true }

    case 'OFFSCREEN_STOP':
      await stopCapture()
      return { ok: true }

    case 'OFFSCREEN_TOGGLE_MIC':
      toggleMic()
      return { ok: true }
  }
}

async function startCapture(streamId: string, meetingId: string, micDeviceId?: string) {
  await stopCapture()

  currentMeetingId = meetingId
  currentMimeType = resolveMimeType()
  audioContext = new AudioContext()
  const destination = audioContext.createMediaStreamDestination()

  tabStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: { chromeMediaSource: 'tab', chromeMediaSourceId: streamId },
    } as unknown as MediaTrackConstraints,
    video: false,
  })

  const tabSource = audioContext.createMediaStreamSource(tabStream)
  tabSource.connect(destination)
  tabSource.connect(audioContext.destination)

  try {
    const audioConstraints: MediaTrackConstraints = micDeviceId
      ? { deviceId: { exact: micDeviceId } }
      : {}
    micStream = await navigator.mediaDevices.getUserMedia({
      audio: audioConstraints,
      video: false,
    })
    audioContext.createMediaStreamSource(micStream).connect(destination)
  } catch {
    micStream = null
  }

  mixedStream = destination.stream
  running = true
  paused = false
  stopping = false
  finalSent = false
  loopPromise = runChunkLoop()
}

function pauseCapture() {
  paused = true
  stopCurrentRecorder()
}

function resumeCapture() {
  paused = false
}

async function stopCapture() {
  if (!running && !mixedStream) return

  stopping = true
  paused = false
  running = false
  stopCurrentRecorder()
  await loopPromise

  if (!finalSent && mixedStream && currentMeetingId) {
    const finalBlob = await recordSingleChunk(FINAL_CHUNK_DURATION_MS)
    if (finalBlob.size > 0) {
      await sendAudioChunk(finalBlob, true)
      finalSent = true
    }
  }

  tabStream?.getTracks().forEach((track) => track.stop())
  micStream?.getTracks().forEach((track) => track.stop())
  await audioContext?.close()

  audioContext = null
  tabStream = null
  micStream = null
  mixedStream = null
  currentRecorder = null
  loopPromise = null
  currentMeetingId = null
  stopping = false
  paused = false
}

async function runChunkLoop() {
  while (running || currentRecorder) {
    if (!currentMeetingId) break
    if (paused) {
      await sleep(200)
      continue
    }

    const blob = await recordSingleChunk(CHUNK_DURATION_MS)
    if (blob.size > 0) {
      const isFinal = stopping || !running
      await sendAudioChunk(blob, isFinal)
      finalSent = isFinal
    }
  }
}

function recordSingleChunk(durationMs: number): Promise<Blob> {
  if (!mixedStream) {
    return Promise.resolve(new Blob([], { type: currentMimeType }))
  }

  return new Promise<Blob>((resolve, reject) => {
    const chunks: Blob[] = []
    const recorder = new MediaRecorder(mixedStream!, {
      mimeType: currentMimeType,
      audioBitsPerSecond: 128_000,
    })
    currentRecorder = recorder

    const timeout = window.setTimeout(() => stopRecorder(recorder), durationMs)

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onerror = () => {
      window.clearTimeout(timeout)
      reject(new Error('MediaRecorder failed while recording audio chunk'))
    }
    recorder.onstop = () => {
      window.clearTimeout(timeout)
      if (currentRecorder === recorder) currentRecorder = null
      resolve(new Blob(chunks, { type: currentMimeType }))
    }

    recorder.start()
  })
}

async function sendAudioChunk(blob: Blob, finalChunk: boolean) {
  if (!currentMeetingId) return
  const buffer = await blob.arrayBuffer()
  const chunk = Array.from(new Uint8Array(buffer))
  await chrome.runtime.sendMessage({
    type: 'AUDIO_CHUNK',
    chunk,
    meetingId: currentMeetingId,
    contentType: blob.type || currentMimeType,
    finalChunk,
  } satisfies ExtMessage)
}

function toggleMic() {
  micStream?.getAudioTracks().forEach((track) => {
    track.enabled = !track.enabled
  })
}

function resolveMimeType(): string {
  if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
    return 'audio/webm;codecs=opus'
  }
  if (MediaRecorder.isTypeSupported('audio/webm')) {
    return 'audio/webm'
  }
  throw new Error('MediaRecorder не поддерживает audio/webm')
}

function stopCurrentRecorder() {
  stopRecorder(currentRecorder)
}

function stopRecorder(recorder: MediaRecorder | null) {
  if (recorder && recorder.state === 'recording') {
    recorder.stop()
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function isOffscreenMessage(msg: unknown): msg is ExtMessage {
  if (typeof msg !== 'object' || msg === null || !('type' in msg)) return false
  return [
    'OFFSCREEN_START',
    'OFFSCREEN_PAUSE',
    'OFFSCREEN_RESUME',
    'OFFSCREEN_STOP',
    'OFFSCREEN_TOGGLE_MIC',
  ].includes(String((msg as { type?: unknown }).type))
}
