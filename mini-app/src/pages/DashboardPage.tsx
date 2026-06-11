import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useMyTasks } from '@/hooks/useTasks'
import { useAppStore } from '@/stores/appStore'
import { TaskCard } from '@/components/common/TaskCard'
import { TaskDetailSheet } from '@/components/common/TaskDetailSheet'
import { CreateTaskSheet } from '@/components/common/CreateTaskSheet'
import { Button } from '@/components/ui/button'
import { isOverdue, isDueToday } from '@/lib/utils'

export function DashboardPage() {
  const tgUser = useAppStore((s) => s.tgUser)
  const { data, isLoading } = useMyTasks()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const tasks = data?.content ?? []
  const overdueTasks = tasks.filter((t) => isOverdue(t.deadline) && !t.completed)
  const todayTasks = tasks.filter((t) => isDueToday(t.deadline) && !t.completed)

  const now = new Date()
  const hour = now.getHours()
  const greeting = hour < 12 ? 'Доброе утро' : hour < 18 ? 'Добрый день' : 'Добрый вечер'

  return (
    <div className="flex flex-col min-h-full">
      <div className="px-4 pt-6 pb-3">
        <h1 className="text-xl font-bold">
          {greeting}{tgUser?.first_name ? `, ${tgUser.first_name}` : ''}
        </h1>
        <p className="text-sm text-muted-foreground">
          {new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(now)}
        </p>
      </div>

      {(overdueTasks.length > 0 || todayTasks.length > 0) && (
        <div className="grid grid-cols-2 gap-3 px-4 mb-4">
          <div className="rounded-xl border bg-destructive/10 p-3 text-center">
            <p className="text-2xl font-bold text-destructive">{overdueTasks.length}</p>
            <p className="text-xs text-muted-foreground">Просрочено</p>
          </div>
          <div className="rounded-xl border bg-yellow-500/10 p-3 text-center">
            <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{todayTasks.length}</p>
            <p className="text-xs text-muted-foreground">Сегодня</p>
          </div>
        </div>
      )}

      <div className="px-4 flex-1">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Мои задачи
          </h2>
          <Button size="sm" variant="ghost" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-xl border bg-card p-3 h-16 animate-pulse bg-muted" />
            ))}
          </div>
        )}

        {!isLoading && tasks.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-4xl mb-3">🎉</p>
            <p className="text-sm">Нет активных задач</p>
          </div>
        )}

        <div className="space-y-2 pb-6">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onClick={() => setSelectedTaskId(task.id)} />
          ))}
        </div>
      </div>

      <TaskDetailSheet taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      <CreateTaskSheet open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
