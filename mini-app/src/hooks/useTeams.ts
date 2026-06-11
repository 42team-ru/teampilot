import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { teamsApi } from '@/api/teams'
import { toast } from 'sonner'

export const teamKeys = {
  all: ['teams'] as const,
  myTeams: () => ['teams', 'my'] as const,
  memberOf: () => ['teams', 'member-of'] as const,
  members: (teamId: string) => ['teams', teamId, 'members'] as const,
  files: (teamId: string) => ['teams', teamId, 'files'] as const,
  workload: (teamId: string) => ['teams', teamId, 'workload'] as const,
}

export function useMyTeams() {
  return useQuery({
    queryKey: teamKeys.myTeams(),
    queryFn: teamsApi.listMyTeams,
    staleTime: 60_000,
  })
}

export function useMemberOfTeams() {
  return useQuery({
    queryKey: teamKeys.memberOf(),
    queryFn: teamsApi.listMemberOf,
    staleTime: 60_000,
  })
}

export function useTeamMembers(teamId: string | undefined) {
  return useQuery({
    queryKey: teamKeys.members(teamId ?? ''),
    queryFn: () => teamsApi.getMembers(teamId!),
    enabled: !!teamId,
    staleTime: 60_000,
  })
}

export function useTeamFiles(teamId: string | undefined) {
  return useQuery({
    queryKey: teamKeys.files(teamId ?? ''),
    queryFn: () => teamsApi.getFiles(teamId!),
    enabled: !!teamId,
    staleTime: 60_000,
  })
}

export function useTeamWorkload(teamId: string | undefined) {
  return useQuery({
    queryKey: teamKeys.workload(teamId ?? ''),
    queryFn: () => teamsApi.getWorkload(teamId!),
    enabled: !!teamId,
    staleTime: 30_000,
  })
}

export function useRemoveMember() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ teamId, teamUserId }: { teamId: string; teamUserId: string }) =>
      teamsApi.removeMember(teamId, teamUserId),
    onSuccess: (_data, { teamId }) => {
      qc.invalidateQueries({ queryKey: teamKeys.members(teamId) })
      toast.success('Участник удалён')
    },
    onError: () => toast.error('Ошибка при удалении участника'),
  })
}

export function useUpdateMemberRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      teamId,
      teamUserId,
      role,
    }: {
      teamId: string
      teamUserId: string
      role: 'MANAGER' | 'PARTICIPANT'
    }) => teamsApi.updateMemberRole(teamId, teamUserId, role),
    onSuccess: (_data, { teamId }) => {
      qc.invalidateQueries({ queryKey: teamKeys.members(teamId) })
    },
  })
}
