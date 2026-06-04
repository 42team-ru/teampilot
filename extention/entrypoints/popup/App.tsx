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

export default function App() {
  const [showSettings, setShowSettings] = useState(false)
  const { state, startRecording, stopRecording, pauseRecording, resumeRecording, toggleMic } =
    useRecordingState()

  if (showSettings) {
    return <SettingsScreen onBack={() => setShowSettings(false)} />
  }

  switch (state.status) {
    case 'idle':
      return <IdleScreen onStart={startRecording} onOpenSettings={() => setShowSettings(true)} />
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
          onRetry={startRecording}
        />
      )
    case 'done':
      return <PostMeetingScreen meetingId={state.meetingId!} />
    default:
      return <IdleScreen onStart={startRecording} onOpenSettings={() => setShowSettings(true)} />
  }
}
