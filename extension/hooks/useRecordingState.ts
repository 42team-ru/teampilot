import { useState, useEffect, useCallback } from 'react'
import { type RecordingState, defaultRecordingState } from '../types/recording'
import { getRecordingState, watchRecordingState } from '../services/storage'
import { sendToBackground } from '../services/messages'
import type { PendingRecordingTarget } from '../services/micPermission'

export function useRecordingState() {
  const [state, setState] = useState<RecordingState>(defaultRecordingState())

  useEffect(() => {
    getRecordingState().then(setState)
    sendToBackground({ type: 'ENSURE_OFFSCREEN' }).catch(() => {})
    return watchRecordingState(setState)
  }, [])

  const ensureMicrophonePermission = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((track) => track.stop())
      return true
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      await sendToBackground({
        type: 'RECORDING_ERROR',
        error: `Не удалось получить доступ к микрофону: ${message}`,
      }).catch(() => {})
      return false
    }
  }, [])

  const startRecording = useCallback(async (target: PendingRecordingTarget) => {
    const response = await sendToBackground({
      type: 'START_RECORDING',
      tabId: target.tabId,
      tabUrl: target.tabUrl,
      tabTitle: target.tabTitle,
      micDeviceId: target.micDeviceId,
    })
    if (response && typeof response === 'object' && 'error' in response) {
      throw new Error(String((response as { error?: unknown }).error ?? 'Failed to start recording'))
    }
  }, [])

  const stopRecording = useCallback(() => sendToBackground({ type: 'STOP_RECORDING' }), [])
  const pauseRecording = useCallback(() => sendToBackground({ type: 'PAUSE_RECORDING' }), [])
  const resumeRecording = useCallback(() => sendToBackground({ type: 'RESUME_RECORDING' }), [])
  const toggleMic = useCallback(() => sendToBackground({ type: 'TOGGLE_MIC' }), [])
  const resetRecording = useCallback(() => sendToBackground({ type: 'RESET_RECORDING' }), [])

  return {
    state,
    ensureMicrophonePermission,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    toggleMic,
    resetRecording,
  }
}
