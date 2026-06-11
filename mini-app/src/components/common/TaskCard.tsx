import { cn, formatDate, isOverdue, isDueToday } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import type { TaskResponse } from '@/api/types'

interface TaskCardProps {
  task: TaskResponse
  onClick?: () => void
  className?: string
}

export function TaskCard({ task, onClick, className }: TaskCardProps) {
  const overdue = isOverdue(task.deadline) && !task.completed
  const today = isDueToday(task.deadline) && !task.completed

  return (
    <div
      onClick={onClick}
      className={cn(
        'rounded-xl border bg-card p-3 space-y-2 active:opacity-70 transition-opacity',
        onClick && 'cursor-pointer',
        className
      )}
    >
      <p className="text-sm font-medium line-clamp-2">{task.title}</p>

      <div className="flex items-center gap-2 flex-wrap">
        {task.column && (
          <Badge variant="secondary" className="text-[10px] h-5">
            {task.column.title}
          </Badge>
        )}
        {task.assignee && (
          <span className="text-xs text-muted-foreground">
            {task.assignee.firstName ?? task.assignee.telegramLogin ?? 'Без ответственного'}
          </span>
        )}
        {task.deadline && (
          <span
            className={cn(
              'text-xs ml-auto',
              overdue ? 'text-destructive font-medium' : today ? 'text-yellow-600 dark:text-yellow-400' : 'text-muted-foreground'
            )}
          >
            {overdue ? '🔴 ' : today ? '🟡 ' : ''}{formatDate(task.deadline)}
          </span>
        )}
      </div>
    </div>
  )
}
