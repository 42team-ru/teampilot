import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, XCircle } from 'lucide-react'
import { syncApi } from '@/api/sync'
import { useAppStore } from '@/stores/appStore'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { toast } from 'sonner'
import { hapticSuccess } from '@/lib/tg'
import { formatDate } from '@/lib/utils'

export function SyncPage() {
  const tgUser = useAppStore((s) => s.tgUser)
  const qc = useQueryClient()

  const { data: activeTasks, isLoading } = useQuery({
    queryKey: ['sync', 'active-tasks', tgUser?.id],
    queryFn: () => syncApi.getActiveTasks(tgUser!.id),
    enabled: !!tgUser,
  })

  const approveTask = useMutation({
    mutationFn: (taskId: string) => syncApi.approveTask(taskId, tgUser!.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync'] })
      hapticSuccess()
      toast.success('Задача подтверждена')
    },
  })

  const rejectTask = useMutation({
    mutationFn: (taskId: string) => syncApi.rejectTask(taskId, tgUser!.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sync'] })
      toast.info('Задача отклонена')
    },
  })

  const excuse = useMutation({
    mutationFn: () => syncApi.excuse(tgUser!.id),
    onSuccess: () => toast.success('Пропущено на сегодня'),
  })

  return (
    <div className="flex flex-col min-h-full px-4 pt-6 pb-6">
      <div className="mb-4">
        <h1 className="text-xl font-bold">Вечерний дайджест</h1>
        <p className="text-sm text-muted-foreground">Что сделал сегодня?</p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="rounded-xl border h-20 animate-pulse bg-muted" />
          ))}
        </div>
      )}

      {!isLoading && (!activeTasks || activeTasks.length === 0) && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-4xl mb-3">✅</p>
            <p className="text-sm">Нет активных задач для дайджеста</p>
          </div>
        </div>
      )}

      {activeTasks && activeTasks.length > 0 && (
        <>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">
            Активные задачи
          </p>
          <div className="space-y-3">
            {activeTasks.map((task) => (
              <Card key={task.id}>
                <CardContent className="p-3">
                  <p className="text-sm font-medium mb-1">{task.title}</p>
                  {task.deadline && (
                    <p className="text-xs text-muted-foreground mb-3">
                      Дедлайн: {formatDate(task.deadline)}
                    </p>
                  )}
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => approveTask.mutate(task.id)}
                      disabled={approveTask.isPending}
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                      Завершено
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-1"
                      onClick={() => rejectTask.mutate(task.id)}
                      disabled={rejectTask.isPending}
                    >
                      <XCircle className="h-3.5 w-3.5 mr-1" />
                      Отложить
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      <div className="mt-auto pt-6">
        <Button
          variant="ghost"
          className="w-full text-muted-foreground"
          onClick={() => excuse.mutate()}
          disabled={excuse.isPending}
        >
          Пропустить дайджест сегодня
        </Button>
      </div>
    </div>
  )
}
