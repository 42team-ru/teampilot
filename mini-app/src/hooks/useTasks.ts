import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { tasksApi, type UpdateTaskRequest } from '@/api/tasks'
import { useAppStore } from '@/stores/appStore'
import { hapticSuccess, hapticError } from '@/lib/tg'
import { toast } from 'sonner'

export const taskKeys = {
  all: ['tasks'] as const,
  my: (telegramId: number) => ['tasks', 'my', telegramId] as const,
  list: (params: object) => ['tasks', 'list', params] as const,
  columns: (chatId: number) => ['tasks', 'columns', chatId] as const,
  detail: (id: string) => ['tasks', id] as const,
}

export function useMyTasks() {
  const tgUser = useAppStore((s) => s.tgUser)
  return useQuery({
    queryKey: taskKeys.my(tgUser?.id ?? 0),
    queryFn: () => tasksApi.listMy(tgUser!.id),
    enabled: !!tgUser,
    staleTime: 30_000,
  })
}

export function useTeamTasks(chatId: number | undefined) {
  return useQuery({
    queryKey: taskKeys.list({ chatId }),
    queryFn: () => tasksApi.list({ chatId, completed: false }),
    enabled: !!chatId,
    staleTime: 30_000,
  })
}

export function useTasksByColumn(columnId: string | undefined) {
  return useQuery({
    queryKey: taskKeys.list({ columnId }),
    queryFn: () => tasksApi.list({ columnId }),
    enabled: !!columnId,
    staleTime: 30_000,
  })
}

export function useTaskColumns(chatId: number | undefined) {
  return useQuery({
    queryKey: taskKeys.columns(chatId ?? 0),
    queryFn: () => tasksApi.listColumns(chatId!),
    enabled: !!chatId,
    staleTime: 60_000,
  })
}

export function useTask(id: string | undefined) {
  return useQuery({
    queryKey: taskKeys.detail(id ?? ''),
    queryFn: () => tasksApi.getById(id!),
    enabled: !!id,
    staleTime: 30_000,
  })
}

export function useUpdateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTaskRequest }) =>
      tasksApi.update(id, data),
    onSuccess: (updated) => {
      qc.setQueryData(taskKeys.detail(updated.id), updated)
      qc.invalidateQueries({ queryKey: taskKeys.all })
      hapticSuccess()
    },
    onError: () => {
      hapticError()
      toast.error('Не удалось обновить задачу')
    },
  })
}

export function useCreateTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: tasksApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.all })
      hapticSuccess()
      toast.success('Задача создана')
    },
    onError: () => {
      hapticError()
      toast.error('Не удалось создать задачу')
    },
  })
}

export function useApproveTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => tasksApi.approve(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taskKeys.all })
      hapticSuccess()
    },
  })
}
