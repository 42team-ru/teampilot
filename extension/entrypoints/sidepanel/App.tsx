import { useState } from 'react'
import { useRecordingState } from '../../hooks/useRecordingState'
import { useMeetingResults } from '../../hooks/useMeetingResults'
import SidePanelHeader from '../../components/sidepanel/SidePanelHeader'
import LiveTab from '../../components/sidepanel/LiveTab'
import TasksTab from '../../components/sidepanel/TasksTab'
import DecisionsTab from '../../components/sidepanel/DecisionsTab'
import SummaryTab from '../../components/sidepanel/SummaryTab'
import SettingsScreen from '../../components/popup/SettingsScreen'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/tabs'
import { useAuthSession } from '../../hooks/useAuthSession'
import AuthRequiredScreen from '../../components/popup/AuthRequiredScreen'
import { useExtensionTheme } from '../../hooks/useExtensionTheme'

export default function App() {
  useExtensionTheme()

  const [showSettings, setShowSettings] = useState(false)
  const auth = useAuthSession()
  const { state, pauseRecording, stopRecording, resumeRecording, toggleMic, resetRecording } = useRecordingState()
  const { results } = useMeetingResults(state.meetingId)

  if (!auth.session) {
    return (
      <div className="flex h-screen items-center justify-center overflow-hidden">
        <AuthRequiredScreen
          loading={auth.loading}
          challenge={auth.challenge}
          error={auth.error}
          fullHeight
          onLogin={auth.login}
        />
      </div>
    )
  }

  if (showSettings) {
    return (
      <div className="flex flex-col h-screen overflow-hidden">
        <SettingsScreen
          onBack={() => setShowSettings(false)}
          authSession={auth.session}
          authLoading={auth.loading}
          authError={auth.error}
          onLogin={auth.login}
          onLogout={auth.logout}
        />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      <SidePanelHeader
        state={state}
        onPause={pauseRecording}
        onResume={resumeRecording}
        onStop={stopRecording}
        onToggleMic={toggleMic}
        onOpenSettings={() => setShowSettings(true)}
        onReset={resetRecording}
      />

      <Tabs defaultValue="live" className="flex-1 flex flex-col overflow-hidden">
        <div className="px-2 pt-2">
          <TabsList className="w-full grid grid-cols-4">
            <TabsTrigger value="live">Live</TabsTrigger>
            <TabsTrigger value="tasks">
              Задачи {results && results.tasks.length > 0 && `(${results.tasks.length})`}
            </TabsTrigger>
            <TabsTrigger value="decisions">Решения</TabsTrigger>
            <TabsTrigger value="summary">Summary</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="live" className="flex-1 overflow-hidden mt-0">
          <LiveTab events={results?.liveEvents ?? []} />
        </TabsContent>

        <TabsContent value="tasks" className="flex-1 overflow-hidden mt-0">
          <TasksTab tasks={results?.tasks ?? []} />
        </TabsContent>

        <TabsContent value="decisions" className="flex-1 overflow-hidden mt-0">
          <DecisionsTab decisions={results?.decisions ?? []} />
        </TabsContent>

        <TabsContent value="summary" className="flex-1 overflow-hidden mt-0">
          <SummaryTab summary={results?.summary} meetingId={state.meetingId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
