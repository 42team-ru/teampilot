import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useMyTasks } from '@/hooks/useTasks'
import { useAppStore } from '@/stores/appStore'
import { usersApi } from '@/api/users'
import { TaskCard } from '@/components/common/TaskCard'
import { TaskDetailSheet } from '@/components/common/TaskDetailSheet'
import { CreateTaskSheet } from '@/components/common/CreateTaskSheet'
import { Button } from '@/components/ui/button'
import { isOverdue, isDueToday } from '@/lib/utils'

export function DashboardPage() {
  const tgUser = useAppStore((s) => s.tgUser)
  const activeTeam = useAppStore((s) => s.activeTeam)
  const navigate = useNavigate()
  const { data, isLoading } = useMyTasks()
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const { data: stats } = useQuery({
    queryKey: ['user-stats', tgUser?.id],
    queryFn: () => usersApi.getStats(tgUser!.id),
    enabled: !!tgUser?.id,
  })

  const tasks = data?.content ?? []
  const overdueTasks = tasks.filter((t) => isOverdue(t.deadline) && !t.completed)
  const todayTasks = tasks.filter(
    (t) => isDueToday(t.deadline) && !t.completed && !isOverdue(t.deadline)
  )
  const remainingTasks = tasks.filter(
    (t) => !t.completed && !isOverdue(t.deadline) && !isDueToday(t.deadline)
  )

  const allEmpty = !isLoading && tasks.length === 0

  const now = new Date()
  const hour = now.getHours()
  const greeting = hour < 12 ? 'Доброе утро' : hour < 18 ? 'Добрый день' : 'Добрый вечер'

  return (
    <div className="flex flex-col min-h-full">
      {/* Header */}
      <div className="px-4 pt-6 pb-3 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">
            {greeting}{tgUser?.first_name ? `, ${tgUser.first_name}` : ''}
          </h1>
          <p className="text-sm text-muted-foreground">
            {new Intl.DateTimeFormat('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' }).format(now)}
          </p>
        </div>
        <Button size="sm" variant="ghost" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* No active team banner */}
      {!activeTeam && (
        <div className="mx-4 mb-3 rounded-xl border border-yellow-500/40 bg-yellow-500/10 p-3 flex items-center justify-between">
          <p className="text-sm text-yellow-700 dark:text-yellow-400">Команда не выбрана</p>
          <Button size="sm" variant="outline" onClick={() => navigate('/teams')}>
            Выбрать команду
          </Button>
        </div>
      )}

      {/* Stats strip */}
      <div className="flex gap-2 px-4 pb-4 overflow-x-auto" style={{ scrollbarWidth: 'none' }}>
        <div className="rounded-xl border bg-card p-3 text-center flex-shrink-0 w-20">
          <p className="text-lg font-bold">🔥</p>
          <p className="text-base font-semibold">{stats?.streakDays ?? '—'}</p>
          <p className="text-[10px] text-muted-foreground leading-tight">Стрик</p>
        </div>
        <div className="rounded-xl border bg-card p-3 text-center flex-shrink-0 w-20">
          <p className="text-lg font-bold">✅</p>
          <p className="text-base font-semibold">{stats?.completedCount ?? '—'}</p>
          <p className="text-[10px] text-muted-foreground leading-tight">Выполнено</p>
        </div>
        <div className="rounded-xl border bg-card p-3 text-center flex-shrink-0 w-20">
          <p className="text-lg font-bold">⏰</p>
          <p className="text-base font-semibold text-destructive">{overdueTasks.length}</p>
          <p className="text-[10px] text-muted-foreground leading-tight">Просрочено</p>
        </div>
        <div className="rounded-xl border bg-card p-3 text-center flex-shrink-0 w-20">
          <p className="text-lg font-bold">📋</p>
          <p className="text-base font-semibold text-yellow-600 dark:text-yellow-400">{todayTasks.length}</p>
          <p className="text-[10px] text-muted-foreground leading-tight">Сегодня</p>
        </div>
      </div>

      {/* Task sections */}
      <div className="px-4 flex-1 space-y-4 pb-6">
        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-xl border bg-card p-3 h-16 animate-pulse bg-muted" />
            ))}
          </div>
        )}

        {allEmpty && (
          <div className="text-center py-12 text-muted-foreground">
            <p className="text-4xl mb-3">🎉</p>
            <p className="text-sm">Нет задач</p>
          </div>
        )}

        {overdueTasks.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-destructive uppercase tracking-wider mb-2">
              Просрочено
            </h2>
            <div className="space-y-2">
              {overdueTasks.map((task) => (
                <div key={task.id} className="border-l-2 border-destructive pl-2">
                  <TaskCard task={task} onClick={() => setSelectedTaskId(task.id)} />
                </div>
              ))}
            </div>
          </div>
        )}

        {todayTasks.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-yellow-600 dark:text-yellow-400 uppercase tracking-wider mb-2">
              На сегодня
            </h2>
            <div className="space-y-2">
              {todayTasks.map((task) => (
                <TaskCard key={task.id} task={task} onClick={() => setSelectedTaskId(task.id)} />
              ))}
            </div>
          </div>
        )}

        {remainingTasks.length > 0 && (
          <div>
            <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              Остальные задачи
            </h2>
            <div className="space-y-2">
              {remainingTasks.map((task) => (
                <TaskCard key={task.id} task={task} onClick={() => setSelectedTaskId(task.id)} />
              ))}
            </div>
          </div>
        )}
      </div>

      <TaskDetailSheet taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      <CreateTaskSheet open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
