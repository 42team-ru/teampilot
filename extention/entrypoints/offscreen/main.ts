let mediaRecorder: MediaRecorder | null = null
let audioContext: AudioContext | null = null
let tabStream: MediaStream | null = null
let micStream: MediaStream | null = null

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  handleMessage(msg).then(sendResponse).catch((e: unknown) => {
    sendResponse({ error: String(e) })
  })
  return true
})

async function handleMessage(msg: { type: string; [key: string]: unknown }) {
  switch (msg.type) {
    case 'OFFSCREEN_START':
      await startCapture(
        msg.streamId as string,
        msg.meetingId as string,
        msg.micDeviceId as string | undefined
      )
      return { ok: true }

    case 'PAUSE_RECORDING':
      if (mediaRecorder?.state === 'recording') mediaRecorder.pause()
      return { ok: true }

    case 'RESUME_RECORDING':
      if (mediaRecorder?.state === 'paused') mediaRecorder.resume()
      return { ok: true }

    case 'STOP_RECORDING':
      await stopCapture()
      return { ok: true }

    case 'OFFSCREEN_TOGGLE_MIC':
      toggleMic()
      return { ok: true }

    default:
      return null
  }
}

function toggleMic() {
  if (!micStream) return
  micStream.getAudioTracks().forEach((t) => {
    t.enabled = !t.enabled
  })
}

async function startCapture(streamId: string, meetingId: string, micDeviceId?: string) {
  audioContext = new AudioContext()
  const dest = audioContext.createMediaStreamDestination()

  tabStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: { chromeMediaSource: 'tab', chromeMediaSourceId: streamId },
    } as unknown as MediaTrackConstraints,
    video: false,
  })
  audioContext.createMediaStreamSource(tabStream).connect(dest)

  try {
    const audioConstraints: MediaTrackConstraints = micDeviceId
      ? { deviceId: { exact: micDeviceId } }
      : {}
    micStream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints })
    audioContext.createMediaStreamSource(micStream).connect(dest)
  } catch {
    // mic denied — continue tab-only
  }

  const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : 'audio/webm'

  mediaRecorder = new MediaRecorder(dest.stream, {
    mimeType,
    audioBitsPerSecond: 128_000,
  })

  mediaRecorder.ondataavailable = async (e) => {
    if (e.data.size === 0) return
    try {
      const buffer = await e.data.arrayBuffer()
      const chunk = Array.from(new Uint8Array(buffer))
      chrome.runtime.sendMessage({ type: 'AUDIO_CHUNK', chunk, meetingId })
    } catch {
      // ignore chunk send errors
    }
  }

  mediaRecorder.onerror = (e) => {
    chrome.runtime.sendMessage({ type: 'RECORDING_ERROR', error: String(e) })
  }

  mediaRecorder.start(5000)
}

async function stopCapture() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
  tabStream?.getTracks().forEach((t) => t.stop())
  micStream?.getTracks().forEach((t) => t.stop())
  await audioContext?.close()
  mediaRecorder = null
  audioContext = null
  tabStream = null
  micStream = null
}
