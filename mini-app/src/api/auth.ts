import { apiClient } from './client'
import type { AuthResponse, TeamResponse } from './types'

export interface TelegramOAuthRequest {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}

export const authApi = {
  loginTelegram: (data: TelegramOAuthRequest) =>
    apiClient.post<AuthResponse>('/auth/telegram', data).then((r) => r.data),

  joinTeam: (teamId: string, telegramId: number) =>
    apiClient
      .post<AuthResponse>(`/auth/invite/${teamId}`, { telegramId })
      .then((r) => r.data),

  createInvite: (chatId: number) =>
    apiClient.post<{ inviteLink: string; teamId: string }>('/auth/invite', { chatId }).then((r) => r.data),

  yougileAuth: (login: string, password: string, companyId?: string) =>
    apiClient.post('/auth/yougile/auth', { login, password, companyId }).then((r) => r.data),

  yougileSelectBoard: (token: string, boardId: string, teamId: string) =>
    apiClient
      .post<TeamResponse>('/auth/yougile/board', { token, boardId, teamId })
      .then((r) => r.data),

  loginWithInitData: () =>
    apiClient.post<AuthResponse>('/auth/telegram/mini-app').then((r) => r.data),
}
