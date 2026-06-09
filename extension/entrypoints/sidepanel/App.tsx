import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'
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
import type { TaskStatusUpdate, Toast } from '../../types/recording'

export default function App() {
  useExtensionTheme()

  const [showSettings, setShowSettings] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const toastTimers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map())

  const auth = useAuthSession()
  const { state, pauseRecording, stopRecording, resumeRecording, toggleMic, resetRecording } = useRecordingState()
  const { results } = useMeetingResults(state.meetingId)

  useEffect(() => {
    chrome.runtime.sendMessage({ type: 'PANEL_OPENED' }).catch(() => {})

    const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
      if (!('pendingToasts' in changes)) return
      const incoming = (changes['pendingToasts'].newValue as TaskStatusUpdate[]) ?? []
      if (incoming.length === 0) return

      const newToasts: Toast[] = incoming.map((event) => ({
        id: `${event.taskId}-${Date.now()}-${Math.random()}`,
        title: toastTitle(event),
        description: event.title,
        variant: toastVariant(event.status),
      }))

      setToasts((prev) => [...prev, ...newToasts].slice(-3))

      newToasts.forEach((toast) => {
        const timer = setTimeout(() => dismissToast(toast.id), 4000)
        toastTimers.current.set(toast.id, timer)
      })

      chrome.storage.session.set({ pendingToasts: [] }).catch(() => {})
    }

    chrome.storage.session.onChanged.addListener(handler)
    return () => {
      chrome.storage.session.onChanged.removeListener(handler)
      toastTimers.current.forEach((t) => clearTimeout(t))
    }
  }, [])

  function dismissToast(id: string) {
    const timer = toastTimers.current.get(id)
    if (timer) {
      clearTimeout(timer)
      toastTimers.current.delete(id)
    }
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

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
    <div className="flex flex-col h-screen overflow-hidden relative">
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

      {toasts.length > 0 && (
        <div className="absolute bottom-4 right-3 left-3 flex flex-col gap-2 z-50 pointer-events-none">
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`flex items-start gap-2 rounded-lg px-3 py-2.5 shadow-lg pointer-events-auto text-sm
                ${toast.variant === 'success' ? 'bg-green-50 border border-green-200 text-green-900' : ''}
                ${toast.variant === 'destructive' ? 'bg-red-50 border border-red-200 text-red-900' : ''}
                ${toast.variant === 'default' ? 'bg-white border border-gray-200 text-gray-900' : ''}
              `}
            >
              <span className="flex-shrink-0 mt-0.5">
                {toast.variant === 'success' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                {toast.variant === 'destructive' && <XCircle className="h-4 w-4 text-red-600" />}
                {toast.variant === 'default' && <Info className="h-4 w-4 text-gray-500" />}
              </span>
              <div className="flex-1 min-w-0">
                <p className="font-medium leading-tight">{toast.title}</p>
                {toast.description && (
                  <p className="text-xs text-gray-600 truncate mt-0.5">{toast.description}</p>
                )}
              </div>
              <button
                onClick={() => dismissToast(toast.id)}
                className="flex-shrink-0 opacity-50 hover:opacity-100 transition-opacity"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function toastTitle(event: TaskStatusUpdate): string {
  switch (event.status) {
    case 'CREATED': return 'Новая задача обнаружена'
    case 'APPROVED': return event.actorName ? `Одобрено: ${event.actorName}` : 'Задача одобрена'
    case 'REJECTED': return event.actorName ? `Отклонено: ${event.actorName}` : 'Задача отклонена'
    default: return 'Обновление задачи'
  }
}

function toastVariant(status: TaskStatusUpdate['status']): Toast['variant'] {
  switch (status) {
    case 'APPROVED': return 'success'
    case 'REJECTED': return 'destructive'
    default: return 'default'
  }
}
