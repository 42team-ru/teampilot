import { apiClient } from './client'
import type { UserResponse } from './types'

export const usersApi = {
  getByTelegramId: (telegramId: number) =>
    apiClient.get<UserResponse>(`/users/${telegramId}`).then((r) => r.data),

  getStats: (telegramId: number) =>
    apiClient.get(`/users/${telegramId}/stats`).then((r) => r.data),

  updateMe: (data: { firstName?: string; lastName?: string }) =>
    apiClient.patch<UserResponse>('/users/me', data).then((r) => r.data),
}
