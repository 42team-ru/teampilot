import { apiClient } from './client'
import type { TeamMemberResponse, TeamResponse, UploadedFileResponse } from './types'

export const teamsApi = {
  listMyTeams: () =>
    apiClient.get<TeamResponse[]>('/teams/my').then((r) => r.data),

  listMemberOf: () =>
    apiClient.get<TeamResponse[]>('/teams/member-of').then((r) => r.data),

  getMembers: (teamId: string) =>
    apiClient.get<TeamMemberResponse[]>(`/teams/${teamId}/members`).then((r) => r.data),

  getFiles: (teamId: string) =>
    apiClient.get<UploadedFileResponse[]>(`/teams/${teamId}/files`).then((r) => r.data),

  update: (teamId: string, data: { chatTitle?: string; kanbanId?: string }) =>
    apiClient.patch<TeamResponse>(`/teams/${teamId}`, data).then((r) => r.data),

  removeMember: (teamId: string, teamUserId: string) =>
    apiClient.delete(`/teams/${teamId}/members/${teamUserId}`),

  updateMemberRole: (teamId: string, teamUserId: string, role: 'MANAGER' | 'PARTICIPANT') =>
    apiClient
      .patch<TeamMemberResponse>(`/teams/${teamId}/members/${teamUserId}/role`, { role })
      .then((r) => r.data),
}
