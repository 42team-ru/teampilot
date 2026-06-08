import { getMeetingByUrl } from '../services/api'
import { requireAuthSession } from '../services/auth'
import {
  clearPendingRecordingTarget,
  getPendingRecordingTarget,
} from '../services/micPermission'
import { connectMeetingSocket, disconnectMeetingSocket, sendMeetingChunk } from '../services/meetingSocket'
import {
  applyMeetingLiveResult,
  getRecordingState,
  resetMeetingResults,
  setRecordingState,
} from '../services/storage'
import { defaultRecordingState, type MeetingAudioChunkPayload, type RecordingState, type TaskStatusUpdate } from '../types/recording'
import type { ExtMessage } from '../types/messages'

const BACKGROUND_MESSAGE_TYPES = new Set([
  'START_RECORDING',
  'STOP_RECORDING',
  'PAUSE_RECORDING',
  'RESUME_RECORDING',
  'TOGGLE_MIC',
  'RESET_RECORDING',
  'ENSURE_OFFSCREEN',
  'AUDIO_CHUNK',
  'RECORDING_ERROR',
  'MIC_PERMISSION_GRANTED',
  'REQUEST_TEST_AUDIO',
  'AUDIO_LEVEL',
  'PANEL_OPENED',
])

let badgeCount = 0

export default defineBackground(() => {
  chrome.alarms.create('keepalive', { periodInMinutes: 0.4 })
  chrome.alarms.onAlarm.addListener(() => {
    // Keeps the MV3 service worker warm while audio is streaming.
  })

  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (!isBackgroundMessage(msg)) return false

    handleMessage(msg, sender).then(sendResponse).catch(async (e: unknown) => {
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

  async function handleMessage(msg: ExtMessage, sender: chrome.runtime.MessageSender) {
    switch (msg.type) {
      case 'START_RECORDING':
        await startRecording(
          msg.tabId,
          msg.tabUrl ?? '',
          msg.tabTitle ?? '',
          msg.micDeviceId
        )
        return { ok: true }

      case 'STOP_RECORDING':
        await stopRecording()
        return { ok: true }

      case 'PAUSE_RECORDING':
        await pauseRecording()
        return { ok: true }

      case 'RESUME_RECORDING':
        await resumeRecording()
        return { ok: true }

      case 'TOGGLE_MIC':
        await toggleMic()
        return { ok: true }

      case 'RESET_RECORDING':
        await setRecordingState(defaultRecordingState())
        return { ok: true }

      case 'ENSURE_OFFSCREEN':
        await ensureOffscreenDocument()
        return { ok: true }

      case 'AUDIO_CHUNK':
        await publishChunk(msg)
        return { ok: true }

      case 'RECORDING_ERROR':
        await updateState({ status: 'error', error: msg.error })
        return { ok: true }

      case 'MIC_PERMISSION_GRANTED':
        await handleMicPermissionGranted(sender)
        return { ok: true }

      case 'REQUEST_TEST_AUDIO':
        return await chrome.runtime.sendMessage({ type: 'OFFSCREEN_TEST_AUDIO' } satisfies ExtMessage)

      case 'AUDIO_LEVEL':
        // Offscreen can only message the service worker — relay via session storage
        // so the popup can watch chrome.storage.onChanged and get real-time levels.
        chrome.storage.session.set({ audioLevel: msg.level }).catch(() => {})
        return { ok: true }

      case 'PANEL_OPENED':
        badgeCount = 0
        chrome.action.setBadgeText({ text: '' }).catch(() => {})
        chrome.storage.session.set({ pendingToasts: [] }).catch(() => {})
        return { ok: true }
    }
  }

  async function notifyTaskUpdate(event: TaskStatusUpdate) {
    const result = await chrome.storage.session.get('pendingToasts')
    const existing = (result['pendingToasts'] as TaskStatusUpdate[]) ?? []
    await chrome.storage.session.set({ pendingToasts: [...existing, event] })
    badgeCount++
    chrome.action.setBadgeText({ text: String(badgeCount) }).catch(() => {})
    chrome.action.setBadgeBackgroundColor({ color: '#ef4444' }).catch(() => {})
  }

  async function startRecording(
    tabId: number,
    tabUrl: string,
    tabTitle: string,
    micDeviceId?: string
  ) {
    const auth = await requireAuthSession()
    if (!tabUrl) {
      throw new Error('Не удалось определить URL текущей вкладки')
    }

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

    const meeting = await getMeetingByUrl(tabUrl)
    if (
      meeting.primaryRecorderTelegramId &&
      meeting.primaryRecorderTelegramId !== auth.telegramId
    ) {
      throw new Error('Этот митинг уже привязан к другому primary recorder')
    }

    await resetMeetingResults(meeting.id)
    await updateState({
      meetingId: meeting.id,
      teamId: meeting.teamId,
      primaryRecorderTelegramId: meeting.primaryRecorderTelegramId,
      startingStep: 1,
    })

    await connectMeetingSocket({
      meetingId: meeting.id,
      teamId: meeting.teamId,
      token: auth.token,
      onResult: async (event) => {
        await applyMeetingLiveResult(event)
        const state = await getRecordingState()
        if (state.status === 'processing') {
          await updateState({ status: 'done' })
        }
      },
      onTaskUpdate: async (event) => {
        await notifyTaskUpdate(event)
      },
      onError: async (error) => {
        await updateState({ error: error.message })
      },
    })

    await updateState({ startingStep: 2 })

    // Ensure offscreen doc is fully ready BEFORE getting streamId — the stream ID
    // from tabCapture has a short lifetime and must be used immediately after retrieval.
    await ensureOffscreenDocument()
    const streamId = await getTabStreamId(tabId)

    let success = false
    let fatalError: Error | null = null
    for (let i = 0; i < 10; i++) {
      try {
        const response = (await chrome.runtime.sendMessage({
          type: 'OFFSCREEN_START',
          streamId,
          meetingId: meeting.id,
          micDeviceId,
        } satisfies ExtMessage)) as { ok?: boolean; error?: string } | undefined
        if (response?.ok) {
          success = true
          break
        }
        if (response?.error) {
          fatalError = new Error(response.error)
          break
        }
      } catch (e) {
        // ignore and retry
      }
      await new Promise((resolve) => setTimeout(resolve, 150))
    }

    if (fatalError) {
      throw fatalError
    }

    if (!success) {
      throw new Error('Не удалось запустить захват звука в фоновом документе (таймаут соединения)')
    }

    await updateState({
      status: 'recording',
      startedAt: Date.now(),
      startingStep: undefined,
    })
  }

  async function pauseRecording() {
    await updateState({ status: 'paused', pausedAt: Date.now() })
    await chrome.runtime.sendMessage({ type: 'OFFSCREEN_PAUSE' } satisfies ExtMessage)
  }

  async function resumeRecording() {
    const state = await getRecordingState()
    const addedPause = state.pausedAt ? Date.now() - state.pausedAt : 0
    await updateState({
      status: 'recording',
      pausedAt: undefined,
      totalPausedMs: (state.totalPausedMs ?? 0) + addedPause,
    })
    await chrome.runtime.sendMessage({ type: 'OFFSCREEN_RESUME' } satisfies ExtMessage)
  }

  async function toggleMic() {
    const state = await getRecordingState()
    const newMuted = !state.micMuted
    await updateState({ micMuted: newMuted })
    await chrome.runtime.sendMessage({ type: 'OFFSCREEN_TOGGLE_MIC' } satisfies ExtMessage)
  }

  async function stopRecording() {
    const state = await getRecordingState()
    if (!state.meetingId) return

    await updateState({ status: 'processing' })
    await chrome.runtime.sendMessage({ type: 'OFFSCREEN_STOP' } satisfies ExtMessage)

    const hasDoc = await chrome.offscreen.hasDocument()
    if (hasDoc) {
      await chrome.offscreen.closeDocument()
    }

    await new Promise((resolve) => setTimeout(resolve, 3000))
    await disconnectMeetingSocket()
    await updateState({ status: 'done' })
  }

  async function handleMicPermissionGranted(sender: chrome.runtime.MessageSender) {
    const pending = await getPendingRecordingTarget()
    if (!pending) {
      throw new Error('Нет ожидающего старта записи после разрешения микрофона')
    }

    if (sender.tab?.id !== undefined) {
      chrome.tabs.remove(sender.tab.id).catch(() => {})
    }

    try {
      await startRecording(
        pending.tabId,
        pending.tabUrl ?? '',
        pending.tabTitle ?? '',
        pending.micDeviceId
      )
    } finally {
      await clearPendingRecordingTarget()
    }
  }

  async function publishChunk(msg: Extract<ExtMessage, { type: 'AUDIO_CHUNK' }>) {
    const state = await getRecordingState()
    const meetingId = state.meetingId ?? msg.meetingId
    if (!meetingId) return

    const bytes = new Uint8Array(msg.chunk)
    const chunkIndex = state.chunks
    const payload: MeetingAudioChunkPayload = {
      chunkIndex,
      audioBase64: bytesToBase64(bytes),
      contentType: msg.contentType || 'audio/webm',
      originalFilename: `meeting-chunk-${String(chunkIndex).padStart(6, '0')}.webm`,
      finalChunk: msg.finalChunk,
    }

    sendMeetingChunk(meetingId, payload)

    await updateState({
      chunks: state.chunks + 1,
      bytes: state.bytes + bytes.byteLength,
    })
  }

  async function getTabStreamId(tabId: number): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      chrome.tabCapture.getMediaStreamId({ targetTabId: tabId }, (id) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
        } else {
          resolve(id)
        }
      })
    })
  }

  async function ensureOffscreenDocument() {
    const hasDoc = await chrome.offscreen.hasDocument()
    if (hasDoc) return

    await chrome.offscreen.createDocument({
      url: chrome.runtime.getURL('offscreen.html'),
      reasons: [
        chrome.offscreen.Reason.USER_MEDIA,
        chrome.offscreen.Reason.AUDIO_PLAYBACK,
      ],
      justification: 'Tab audio capture and playback for meeting recording',
    })
  }
})

function isBackgroundMessage(msg: unknown): msg is ExtMessage {
  return (
    typeof msg === 'object' &&
    msg !== null &&
    'type' in msg &&
    typeof (msg as { type?: unknown }).type === 'string' &&
    BACKGROUND_MESSAGE_TYPES.has((msg as { type: string }).type)
  )
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = ''
  const batchSize = 0x8000
  for (let i = 0; i < bytes.length; i += batchSize) {
    const chunk = bytes.subarray(i, i + batchSize)
    binary += String.fromCharCode(...chunk)
  }
  return btoa(binary)
}
