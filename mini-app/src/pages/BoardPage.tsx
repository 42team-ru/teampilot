import { useState } from 'react'
import { Plus } from 'lucide-react'
import { useTaskColumns, useTasksByColumn, useUpdateTask } from '@/hooks/useTasks'
import { useTeamMembers } from '@/hooks/useTeams'
import { useAppStore } from '@/stores/appStore'
import { TaskCard } from '@/components/common/TaskCard'
import { TaskDetailSheet } from '@/components/common/TaskDetailSheet'
import { CreateTaskSheet } from '@/components/common/CreateTaskSheet'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { TaskColumnResponse } from '@/api/types'

function KanbanColumn({
  column,
  filterMemberId,
  onTaskClick,
}: {
  column: TaskColumnResponse
  filterMemberId: string | null
  onTaskClick: (id: string) => void
}) {
  const { data } = useTasksByColumn(column.id)
  const tasks = (data?.content ?? []).filter(
    (t) => !filterMemberId || t.assignee?.teamUserId === filterMemberId
  )

  const colors: Record<number, string> = {
    0: 'border-t-slate-400',
    1: 'border-t-blue-400',
    2: 'border-t-yellow-400',
    3: 'border-t-green-400',
  }

  return (
    <div className="flex-shrink-0 w-64">
      <div className={cn('rounded-xl border border-t-4 bg-card overflow-hidden', colors[0] ?? 'border-t-slate-400')}>
        <div className="px-3 py-2 flex items-center justify-between border-b">
          <span className="text-sm font-semibold">{column.title}</span>
          <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">{tasks.length}</span>
        </div>
        <div className="p-2 space-y-2 min-h-[100px]">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onClick={() => onTaskClick(task.id)} />
          ))}
        </div>
      </div>
    </div>
  )
}

export function BoardPage() {
  const activeTeam = useAppStore((s) => s.activeTeam)
  const { data: columns, isLoading } = useTaskColumns(activeTeam?.telegramChatId)
  const { data: members } = useTeamMembers(activeTeam?.id)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [filterMemberId, setFilterMemberId] = useState<string | null>(null)

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-6 pb-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">Доска</h1>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Задача
        </Button>
      </div>

      {members && members.length > 1 && (
        <div className="px-4 pb-3 flex gap-2 overflow-x-auto scrollbar-none">
          <button
            onClick={() => setFilterMemberId(null)}
            className={cn(
              'flex-shrink-0 text-xs border rounded-full px-3 py-1.5 transition-colors',
              !filterMemberId ? 'bg-primary text-primary-foreground border-primary' : 'bg-background'
            )}
          >
            Все
          </button>
          {members.map((m) => (
            <button
              key={m.id}
              onClick={() => setFilterMemberId(m.id === filterMemberId ? null : m.id)}
              className={cn(
                'flex-shrink-0 text-xs border rounded-full px-3 py-1.5 transition-colors',
                m.id === filterMemberId ? 'bg-primary text-primary-foreground border-primary' : 'bg-background'
              )}
            >
              {m.firstName ?? m.telegramLogin ?? m.telegramId}
            </button>
          ))}
        </div>
      )}

      {isLoading && (
        <div className="flex gap-3 px-4 overflow-x-auto">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex-shrink-0 w-64 h-48 rounded-xl border animate-pulse bg-muted" />
          ))}
        </div>
      )}

      {!isLoading && (!columns || columns.length === 0) && (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center">
            <p className="text-4xl mb-3">📋</p>
            <p className="text-sm">Нет колонок. Настройте YouGile в профиле команды.</p>
          </div>
        </div>
      )}

      {columns && columns.length > 0 && (
        <div className="flex-1 overflow-x-auto">
          <div className="flex gap-3 px-4 pb-6 h-full" style={{ minWidth: `${columns.length * 280}px` }}>
            {columns.map((col) => (
              <KanbanColumn
                key={col.id}
                column={col}
                filterMemberId={filterMemberId}
                onTaskClick={setSelectedTaskId}
              />
            ))}
          </div>
        </div>
      )}

      <TaskDetailSheet taskId={selectedTaskId} onClose={() => setSelectedTaskId(null)} />
      <CreateTaskSheet open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  )
}
