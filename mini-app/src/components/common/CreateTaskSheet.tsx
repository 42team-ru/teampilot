import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useCreateTask } from '@/hooks/useTasks'
import { useTeamMembers, useMyTeams } from '@/hooks/useTeams'
import { useAppStore } from '@/stores/appStore'
import { useTaskColumns } from '@/hooks/useTasks'

const schema = z.object({
  title: z.string().min(1, 'Обязательное поле'),
  description: z.string().optional(),
  deadline: z.string().optional(),
  columnId: z.string().optional(),
  assigneeTeamUserId: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface CreateTaskSheetProps {
  open: boolean
  onClose: () => void
}

export function CreateTaskSheet({ open, onClose }: CreateTaskSheetProps) {
  const activeTeam = useAppStore((s) => s.activeTeam)
  const createTask = useCreateTask()
  const { data: members } = useTeamMembers(activeTeam?.id)
  const { data: columns } = useTaskColumns(activeTeam?.telegramChatId)

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: FormData) => {
    if (!activeTeam) return
    createTask.mutate(
      {
        teamId: activeTeam.id,
        title: data.title,
        description: data.description,
        deadline: data.deadline ? new Date(data.deadline).toISOString() : undefined,
        columnId: data.columnId,
        assigneeTeamUserId: data.assigneeTeamUserId,
      },
      { onSuccess: () => { reset(); onClose() } }
    )
  }

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="bottom" className="pb-8">
        <SheetHeader className="pt-4">
          <SheetTitle>Новая задача</SheetTitle>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="px-4 space-y-3 mt-2">
          <div>
            <Input placeholder="Название задачи *" {...register('title')} />
            {errors.title && <p className="text-xs text-destructive mt-1">{errors.title.message}</p>}
          </div>

          <Textarea placeholder="Описание (опционально)" rows={3} {...register('description')} />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Дедлайн</p>
              <Input type="datetime-local" {...register('deadline')} />
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Колонка</p>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                {...register('columnId')}
              >
                <option value="">—</option>
                {columns?.map((c) => (
                  <option key={c.id} value={c.id}>{c.title}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <p className="text-xs text-muted-foreground mb-1">Ответственный</p>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              {...register('assigneeTeamUserId')}
            >
              <option value="">—</option>
              {members?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.firstName ?? m.telegramLogin ?? m.telegramId}
                </option>
              ))}
            </select>
          </div>

          <Button type="submit" className="w-full" disabled={createTask.isPending}>
            {createTask.isPending ? 'Создание...' : 'Создать задачу'}
          </Button>
        </form>
      </SheetContent>
    </Sheet>
  )
}
