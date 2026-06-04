import { useState, useEffect, useCallback } from 'react'
import { type RecordingState, defaultRecordingState } from '../types/recording'
import { getRecordingState, watchRecordingState } from '../services/storage'
import { sendToBackground } from '../services/messages'
import { getMicSettings } from '../services/micSettings'

export function useRecordingState() {
  const [state, setState] = useState<RecordingState>(defaultRecordingState())

  useEffect(() => {
    getRecordingState().then(setState)
    return watchRecordingState(setState)
  }, [])

  const startRecording = useCallback(async () => {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true })
    const tab = tabs[0]
    if (!tab?.id) return
    const micSettings = await getMicSettings()
    await sendToBackground({
      type: 'START_RECORDING',
      tabId: tab.id,
      tabUrl: tab.url,
      tabTitle: tab.title,
      micDeviceId: micSettings?.deviceId,
    })
  }, [])

  const stopRecording = useCallback(() => sendToBackground({ type: 'STOP_RECORDING' }), [])
  const pauseRecording = useCallback(() => sendToBackground({ type: 'PAUSE_RECORDING' }), [])
  const resumeRecording = useCallback(() => sendToBackground({ type: 'RESUME_RECORDING' }), [])
  const toggleMic = useCallback(() => sendToBackground({ type: 'TOGGLE_MIC' }), [])

  return { state, startRecording, stopRecording, pauseRecording, resumeRecording, toggleMic }
}
