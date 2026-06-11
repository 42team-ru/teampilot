import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTask, useUpdateTask, useApproveTask } from '@/hooks/useTasks'
import { useTeamMembers } from '@/hooks/useTeams'
import { useAppStore } from '@/stores/appStore'
import { formatDate, isOverdue } from '@/lib/utils'
import { CheckCircle2, XCircle } from 'lucide-react'

interface TaskDetailSheetProps {
  taskId: string | null
  onClose: () => void
}

export function TaskDetailSheet({ taskId, onClose }: TaskDetailSheetProps) {
  const { data: task } = useTask(taskId ?? undefined)
  const activeTeam = useAppStore((s) => s.activeTeam)
  const { data: members } = useTeamMembers(activeTeam?.id)
  const updateTask = useUpdateTask()
  const approveTask = useApproveTask()

  if (!task) return null

  const overdue = isOverdue(task.deadline)

  return (
    <Sheet open={!!taskId} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="bottom" className="pb-8">
        <SheetHeader className="pt-4">
          <SheetTitle className="pr-8">{task.title}</SheetTitle>
          <div className="flex items-center gap-2 flex-wrap">
            {task.column && <Badge variant="secondary">{task.column.title}</Badge>}
            {task.localStatus === 'PENDING_APPROVAL' && (
              <Badge variant="warning">Ожидает подтверждения</Badge>
            )}
            {task.completed && <Badge variant="success">Завершена</Badge>}
            {overdue && !task.completed && <Badge variant="destructive">Просрочена</Badge>}
          </div>
        </SheetHeader>

        <div className="px-4 space-y-4 mt-2">
          {task.description && (
            <p className="text-sm text-muted-foreground">{task.description}</p>
          )}

          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground text-xs mb-1">Ответственный</p>
              <p>{task.assignee?.firstName ?? task.assignee?.telegramLogin ?? '—'}</p>
            </div>
            <div>
              <p className="text-muted-foreground text-xs mb-1">Дедлайн</p>
              <p className={overdue ? 'text-destructive' : ''}>{formatDate(task.deadline)}</p>
            </div>
          </div>

          {members && (
            <div>
              <p className="text-muted-foreground text-xs mb-2">Переназначить</p>
              <div className="flex gap-2 flex-wrap">
                {members.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => updateTask.mutate({ id: task.id, data: { assigneeTeamUserId: m.id } })}
                    className="text-xs border rounded-full px-3 py-1 hover:bg-accent transition-colors"
                  >
                    {m.firstName ?? m.telegramLogin ?? m.telegramId}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            {task.localStatus === 'PENDING_APPROVAL' && (
              <Button
                className="flex-1"
                onClick={() => { approveTask.mutate(task.id); onClose() }}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Подтвердить
              </Button>
            )}
            {!task.completed && task.localStatus === 'ACTIVE' && (
              <Button
                className="flex-1"
                onClick={() => { updateTask.mutate({ id: task.id, data: {} }); onClose() }}
              >
                <CheckCircle2 className="h-4 w-4 mr-2" />
                Завершить
              </Button>
            )}
            <Button variant="outline" onClick={onClose} className="flex-1">
              <XCircle className="h-4 w-4 mr-2" />
              Закрыть
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
