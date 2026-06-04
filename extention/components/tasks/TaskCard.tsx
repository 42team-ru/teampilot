import { useState } from 'react'
import { UserRound, Calendar, Target } from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import type { Task } from '../../types/recording'

interface Props {
  task: Task
  onCreateTask?: (taskId: string, assignee?: string) => void
  onRejectTask?: (taskId: string) => void
}

const STATUS_LABELS: Record<Task['status'], { label: string; variant: 'warning' | 'success' | 'destructive' | 'secondary' }> = {
  pending: { label: 'Требует подтверждения', variant: 'warning' },
  created: { label: 'Создана', variant: 'success' },
  rejected: { label: 'Отклонена', variant: 'destructive' },
  incomplete: { label: 'Не хватает данных', variant: 'secondary' },
}

export default function TaskCard({ task, onCreateTask, onRejectTask }: Props) {
  const [assigneeInput, setAssigneeInput] = useState('')
  const [showAssigneeInput, setShowAssigneeInput] = useState(false)
  const { label, variant } = STATUS_LABELS[task.status]

  const handleCreate = () => {
    if (!task.assignee && !assigneeInput) {
      setShowAssigneeInput(true)
      return
    }
    onCreateTask?.(task.id, assigneeInput || task.assignee)
  }

  return (
    <Card className="mb-2">
      <CardContent className="p-3 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium leading-snug">{task.title}</p>
          <Badge variant={variant} className="flex-shrink-0 text-xs">{label}</Badge>
        </div>

        <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
          {task.assignee ? (
            <span className="flex items-center gap-1">
              <UserRound className="h-3 w-3" />{task.assignee}
            </span>
          ) : (
            <span className="flex items-center gap-1 text-amber-600">
              <UserRound className="h-3 w-3" />Исполнитель не найден
            </span>
          )}
          {task.deadline && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />{task.deadline}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Target className="h-3 w-3" />AI: {Math.round(task.confidence * 100)}%
          </span>
        </div>

        {task.source && (
          <p className="text-xs text-muted-foreground italic truncate">Источник: {task.source}</p>
        )}

        {showAssigneeInput && !task.assignee && (
          <div className="space-y-2">
            <input
              className="w-full rounded border px-2 py-1 text-xs"
              placeholder="Введите имя исполнителя..."
              value={assigneeInput}
              onChange={(e) => setAssigneeInput(e.target.value)}
              autoFocus
            />
            <div className="flex gap-1">
              <Button size="sm" className="flex-1 text-xs h-7" onClick={() => onCreateTask?.(task.id, assigneeInput)}>
                Назначить
              </Button>
              <Button size="sm" variant="outline" className="text-xs h-7" onClick={() => onCreateTask?.(task.id, 'me')}>
                Мне
              </Button>
              <Button size="sm" variant="ghost" className="text-xs h-7" onClick={() => setShowAssigneeInput(false)}>
                Пропустить
              </Button>
            </div>
          </div>
        )}

        {task.status === 'pending' && !showAssigneeInput && (
          <div className="flex gap-1 pt-1">
            <Button size="sm" className="flex-1 text-xs h-7" onClick={handleCreate}>
              Создать
            </Button>
            <Button size="sm" variant="destructive" className="flex-1 text-xs h-7" onClick={() => onRejectTask?.(task.id)}>
              Отклонить
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
