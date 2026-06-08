import { useState } from 'react'
import { useRecordingState } from '../../hooks/useRecordingState'
import IdleScreen from '../../components/popup/IdleScreen'
import StartingScreen from '../../components/popup/StartingScreen'
import RecordingScreen from '../../components/popup/RecordingScreen'
import PausedScreen from '../../components/popup/PausedScreen'
import ProcessingScreen from '../../components/popup/ProcessingScreen'
import ErrorScreen from '../../components/popup/ErrorScreen'
import SettingsScreen from '../../components/popup/SettingsScreen'
import PostMeetingScreen from '../../components/post-meeting/PostMeetingScreen'
import { useAuthSession } from '../../hooks/useAuthSession'
import AuthRequiredScreen from '../../components/popup/AuthRequiredScreen'
import { getMicSettings } from '../../services/micSettings'
import { useExtensionTheme } from '../../hooks/useExtensionTheme'
import {
  clearPendingRecordingTarget,
  getPendingRecordingTarget,
  openMicrophonePermissionPage,
  setPendingRecordingTarget,
  type PendingRecordingTarget,
} from '../../services/micPermission'

export default function App() {
  useExtensionTheme()

  const [showSettings, setShowSettings] = useState(false)
  const auth = useAuthSession()
  const {
    state,
    ensureMicrophonePermission,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    toggleMic,
    resetRecording,
  } =
    useRecordingState()

  const buildRecordingTarget = async (): Promise<PendingRecordingTarget | null> => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true })
    if (!tab?.id) return null

    const micSettings = await getMicSettings()
    return {
      tabId: tab.id,
      tabUrl: tab.url,
      tabTitle: tab.title,
      micDeviceId: micSettings?.deviceId,
    }
  }

  const handleStart = async () => {
    const target = await buildRecordingTarget()
    if (!target) return

    await setPendingRecordingTarget(target)
    const micReady = await ensureMicrophonePermission()
    if (!micReady) return

    const session = auth.session ?? (await auth.login())
    if (!session) return

    try {
      await startRecording(target)
    } catch (e) {
      console.warn('Failed to start recording:', e)
    } finally {
      await clearPendingRecordingTarget().catch(() => {})
    }
  }

  const handleRetry = async () => {
    const target = (await getPendingRecordingTarget()) ?? (await buildRecordingTarget())
    if (!target) return

    await setPendingRecordingTarget(target)
    await openMicrophonePermissionPage()
  }

  if (!auth.session) {
    return (
      <AuthRequiredScreen
        loading={auth.loading}
        challenge={auth.challenge}
        error={auth.error}
        onLogin={auth.login}
      />
    )
  }

  if (showSettings) {
    return (
      <SettingsScreen
        onBack={() => setShowSettings(false)}
        authSession={auth.session}
        authLoading={auth.loading}
        authError={auth.error}
        onLogin={auth.login}
        onLogout={auth.logout}
      />
    )
  }

  switch (state.status) {
    case 'idle':
      return (
        <IdleScreen
          authSession={auth.session}
          authLoading={auth.loading}
          authError={auth.error}
          onStart={handleStart}
          onLogin={auth.login}
          onOpenSettings={() => setShowSettings(true)}
        />
      )
    case 'starting':
      return <StartingScreen state={state} />
    case 'recording':
      return (
        <RecordingScreen
          state={state}
          onPause={pauseRecording}
          onStop={stopRecording}
          onToggleMic={toggleMic}
        />
      )
    case 'paused':
      return <PausedScreen state={state} onResume={resumeRecording} onStop={stopRecording} />
    case 'processing':
      return <ProcessingScreen />
    case 'error':
      return (
        <ErrorScreen
          error={state.error ?? 'Неизвестная ошибка'}
          onRetry={handleRetry}
        />
      )
    case 'done':
      return <PostMeetingScreen meetingId={state.meetingId!} onReset={resetRecording} />
    default:
      return (
        <IdleScreen
          authSession={auth.session}
          authLoading={auth.loading}
          authError={auth.error}
          onStart={handleStart}
          onLogin={auth.login}
          onOpenSettings={() => setShowSettings(true)}
        />
      )
  }
}
