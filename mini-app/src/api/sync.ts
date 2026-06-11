import { apiClient } from './client'
import type { SyncActiveTask } from './types'

export const syncApi = {
  getActiveTasks: (telegramUserId: number) =>
    apiClient
      .get<SyncActiveTask[]>('/sync/active-tasks', { params: { telegramUserId } })
      .then((r) => r.data),

  approveTask: (taskId: string, telegramUserId: number) =>
    apiClient.post('/sync/approve-task', { taskId, telegramUserId }),

  rejectTask: (taskId: string, telegramUserId: number) =>
    apiClient.post('/sync/reject-task', { taskId, telegramUserId }),

  approveProposal: (proposalId: string, telegramUserId: number) =>
    apiClient.post('/sync/approve-proposal', { proposalId, telegramUserId }),

  rejectProposal: (proposalId: string, telegramUserId: number) =>
    apiClient.post('/sync/reject-proposal', { proposalId, telegramUserId }),

  excuse: (telegramUserId: number, teamId?: string) =>
    apiClient.post('/sync/excuse', { telegramUserId, teamId }),
}
