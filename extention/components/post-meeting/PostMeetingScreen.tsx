import { ExternalLink, Send, ListChecks, Loader2, AlertCircle } from 'lucide-react'
import { Button } from '../ui/button'
import { useMeetingResults } from '../../hooks/useMeetingResults'
import { formatDuration } from '../../lib/utils'

interface Props {
  meetingId: string
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border p-3 text-center">
      <p className="text-muted-foreground text-xs">{label}</p>
      <p className="text-xl font-bold mt-0.5">{value}</p>
    </div>
  )
}

export default function PostMeetingScreen({ meetingId }: Props) {
  const { results, loading, error } = useMeetingResults(meetingId)

  const openPanel = async () => {
    const win = await chrome.windows.getCurrent()
    if (win.id !== undefined) {
      chrome.sidePanel.open({ windowId: win.id }).catch(() => {})
    }
  }

  const createAllTasks = async () => {
    if (!results) return
    const pending = results.tasks.filter((t) => t.status === 'pending')
    for (const task of pending) {
      const { createTask } = await import('../../services/api')
      await createTask(meetingId, task.id).catch(() => {})
    }
  }

  if (loading) {
    return (
      <div className="w-[360px] p-6 flex flex-col items-center gap-3">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Загрузка результатов...</p>
      </div>
    )
  }

  if (error || !results) {
    return (
      <div className="w-[360px] p-4 space-y-4">
        <div className="flex items-center gap-2 text-destructive">
          <AlertCircle className="h-5 w-5" />
          <span className="font-semibold text-sm">Встреча завершена</span>
        </div>
        <p className="text-xs text-muted-foreground">Результаты обрабатываются...</p>
        <Button className="w-full" onClick={openPanel}>
          <ExternalLink className="h-3.5 w-3.5 mr-2" /> Открыть панель
        </Button>
      </div>
    )
  }

  const durationSec = Math.floor(results.duration / 1000)

  return (
    <div className="w-[360px] p-4 space-y-4">
      <div>
        <p className="font-semibold text-sm">Встреча обработана</p>
        <p className="text-xs text-muted-foreground">Продолжительность: {formatDuration(durationSec)}</p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <StatCard label="Задач" value={results.tasks.length} />
        <StatCard label="Решений" value={results.decisions.length} />
        <StatCard label="Рисков" value={results.summary?.risks?.length ?? 0} />
      </div>

      <div className="space-y-2">
        <Button className="w-full" size="sm" onClick={openPanel}>
          <ExternalLink className="h-3.5 w-3.5 mr-2" /> Открыть результаты
        </Button>
        <Button className="w-full" size="sm" variant="outline" disabled>
          <Send className="h-3.5 w-3.5 mr-2" /> Отправить в Telegram
        </Button>
        <Button className="w-full" size="sm" variant="outline" onClick={createAllTasks}
          disabled={results.tasks.filter((t) => t.status === 'pending').length === 0}>
          <ListChecks className="h-3.5 w-3.5 mr-2" />
          Создать задачи ({results.tasks.filter((t) => t.status === 'pending').length})
        </Button>
      </div>
    </div>
  )
}
