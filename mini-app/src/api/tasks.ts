import { apiClient } from './client'
import type { PageResponse, TaskColumnResponse, TaskResponse } from './types'

export interface CreateUserTaskRequest {
  teamId: string
  title: string
  description?: string
  deadline?: string
  columnId?: string
  assigneeTeamUserId?: string
}

export interface UpdateTaskRequest {
  title?: string
  description?: string
  deadline?: string
  columnId?: string
  assigneeTeamUserId?: string
}

export const tasksApi = {
  getById: (id: string) =>
    apiClient.get<TaskResponse>(`/tasks/${id}`).then((r) => r.data),

  listMy: (assignee: number, page = 0, size = 20) =>
    apiClient
      .get<PageResponse<TaskResponse>>('/tasks/my', { params: { assignee, page, size } })
      .then((r) => r.data),

  list: (params: {
    chatId?: number
    assignee?: number
    completed?: boolean
    columnId?: string
    pendingApproval?: boolean
    page?: number
    size?: number
  }) => apiClient.get<PageResponse<TaskResponse>>('/tasks', { params }).then((r) => r.data),

  listColumns: (chatId: number) =>
    apiClient.get<TaskColumnResponse[]>('/tasks/columns', { params: { chatId } }).then((r) => r.data),

  create: (data: CreateUserTaskRequest) =>
    apiClient.post<TaskResponse>('/tasks/user', data).then((r) => r.data),

  update: (id: string, data: UpdateTaskRequest) =>
    apiClient.patch<TaskResponse>(`/tasks/${id}`, data).then((r) => r.data),

  approve: (id: string) =>
    apiClient.post<TaskResponse>(`/tasks/${id}/approve`).then((r) => r.data),

  cancel: (id: string) =>
    apiClient.post<TaskResponse>(`/tasks/${id}/cancel`).then((r) => r.data),
}
