import { defaultRecordingState, type RecordingState } from '../types/recording'
import { setRecordingState, getRecordingState } from '../services/storage'
import { startMeeting, sendChunk, finishMeeting, getMeetingResults } from '../services/api'

export default defineBackground(() => {
  chrome.alarms.create('keepalive', { periodInMinutes: 0.4 })
  chrome.alarms.onAlarm.addListener(() => {
    // keeps SW alive during recording
  })

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    handleMessage(msg).then(sendResponse).catch(async (e: unknown) => {
      const error = e instanceof Error ? e.message : String(e)
      await updateState({ status: 'error', error })
      sendResponse({ error })
    })
    return true
  })

  async function updateState(patch: Partial<RecordingState>) {
    const current = await getRecordingState()
    await setRecordingState({ ...current, ...patch })
  }

  async function handleMessage(msg: { type: string; [key: string]: unknown }) {
    switch (msg.type) {
      case 'START_RECORDING':
        await startRecording(
          msg.tabId as number,
          (msg.tabUrl as string) ?? '',
          (msg.tabTitle as string) ?? '',
          msg.micDeviceId as string | undefined
        )
        break

      case 'STOP_RECORDING':
        await stopRecording()
        break

      case 'PAUSE_RECORDING': {
        await updateState({ status: 'paused', pausedAt: Date.now() })
        chrome.runtime.sendMessage({ type: 'PAUSE_RECORDING' }).catch(() => {})
        break
      }

      case 'RESUME_RECORDING': {
        const state = await getRecordingState()
        const addedPause = state.pausedAt ? Date.now() - state.pausedAt : 0
        await updateState({
          status: 'recording',
          pausedAt: undefined,
          totalPausedMs: (state.totalPausedMs ?? 0) + addedPause,
        })
        chrome.runtime.sendMessage({ type: 'RESUME_RECORDING' }).catch(() => {})
        break
      }

      case 'TOGGLE_MIC': {
        const state = await getRecordingState()
        const newMuted = !state.micMuted
        await updateState({ micMuted: newMuted })
        chrome.runtime.sendMessage({ type: 'OFFSCREEN_TOGGLE_MIC' }).catch(() => {})
        break
      }

      case 'AUDIO_CHUNK': {
        const { chunk, meetingId } = msg as unknown as { chunk: number[]; meetingId: string }
        const state = await getRecordingState()
        if (!meetingId) break
        const blob = new Blob([new Uint8Array(chunk)], { type: 'audio/webm;codecs=opus' })
        const chunkIndex = state.chunks
        sendChunk(meetingId, blob, chunkIndex).catch(() => {})
        await updateState({
          chunks: state.chunks + 1,
          bytes: state.bytes + blob.size,
        })
        break
      }
    }
  }

  async function startRecording(
    tabId: number,
    tabUrl: string,
    tabTitle: string,
    micDeviceId?: string
  ) {
    await setRecordingState({
      ...defaultRecordingState(),
      status: 'starting',
      startingStep: 0,
      tabId,
      tabUrl,
      tabTitle,
      micEnabled: true,
      micMuted: false,
      micDeviceId,
    })

    const streamId = await new Promise<string>((resolve, reject) => {
      chrome.tabCapture.getMediaStreamId({ targetTabId: tabId }, (id) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
        } else {
          resolve(id)
        }
      })
    })
    await updateState({ startingStep: 1 })

    const { meetingId } = await startMeeting(tabTitle || tabUrl)
    await updateState({ meetingId, startingStep: 2 })

    const hasDoc = await chrome.offscreen.hasDocument()
    if (!hasDoc) {
      await chrome.offscreen.createDocument({
        url: chrome.runtime.getURL('offscreen.html'),
        reasons: [chrome.offscreen.Reason.USER_MEDIA],
        justification: 'Tab audio capture for meeting recording',
      })
    }

    await new Promise((r) => setTimeout(r, 200))

    chrome.runtime.sendMessage({
      type: 'OFFSCREEN_START',
      streamId,
      meetingId,
      micDeviceId,
    }).catch(() => {})

    await updateState({
      status: 'recording',
      startedAt: Date.now(),
      startingStep: undefined,
    })
  }

  async function stopRecording() {
    const state = await getRecordingState()
    if (!state.meetingId) return

    await updateState({ status: 'processing' })

    chrome.runtime.sendMessage({ type: 'STOP_RECORDING' }).catch(() => {})

    await new Promise((r) => setTimeout(r, 1200))

    await finishMeeting(state.meetingId).catch(() => {})

    const hasDoc = await chrome.offscreen.hasDocument()
    if (hasDoc) {
      await chrome.offscreen.closeDocument()
    }

    await pollForResults(state.meetingId)
  }

  async function pollForResults(meetingId: string) {
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 3000))
      try {
        const results = await getMeetingResults(meetingId)
        if (results?.tasks !== undefined) {
          await updateState({ status: 'done' })
          return
        }
      } catch {
        // not ready yet
      }
    }
    await updateState({ status: 'done' })
  }
})
