import { useState } from 'react'
import { ChevronRight, Crown, UserMinus, RefreshCw } from 'lucide-react'
import { useMyTeams, useMemberOfTeams, useTeamMembers, useTeamFiles, useRemoveMember, useUpdateMemberRole } from '@/hooks/useTeams'
import { useAppStore } from '@/stores/appStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import type { TeamResponse } from '@/api/types'
import { cn } from '@/lib/utils'
import { authApi } from '@/api/auth'
import { toast } from 'sonner'

function TeamDetailSheet({ team, onClose }: { team: TeamResponse; onClose: () => void }) {
  const { data: members } = useTeamMembers(team.id)
  const { data: files } = useTeamFiles(team.id)
  const removeMember = useRemoveMember()
  const updateRole = useUpdateMemberRole()
  const setActiveTeam = useAppStore((s) => s.setActiveTeam)

  const handleCopyInvite = async () => {
    if (!team.telegramChatId) {
      toast.error('Нет привязанного чата')
      return
    }
    try {
      const data = await authApi.createInvite(team.telegramChatId)
      await navigator.clipboard.writeText(data.inviteLink ?? '')
      toast.success('Ссылка скопирована')
    } catch {
      toast.error('Не удалось создать инвайт')
    }
  }

  return (
    <Sheet open onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="bottom" className="pb-8">
        <SheetHeader className="pt-4">
          <SheetTitle>{team.chatTitle ?? 'Команда'}</SheetTitle>
        </SheetHeader>

        <div className="px-4 space-y-4 mt-2">
          <div className="flex gap-2">
            <Button size="sm" variant="outline" className="flex-1" onClick={handleCopyInvite}>
              Пригласить
            </Button>
            <Button size="sm" variant="outline" className="flex-1" onClick={() => { setActiveTeam(team); onClose() }}>
              Выбрать
            </Button>
          </div>

          {members && members.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                Участники ({members.length})
              </p>
              <div className="space-y-2">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center text-xs font-medium">
                      {(m.firstName ?? m.telegramLogin ?? '?')[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {m.firstName} {m.lastName}
                      </p>
                      <p className="text-xs text-muted-foreground">@{m.telegramLogin ?? m.telegramId}</p>
                    </div>
                    <Badge variant={m.role === 'MANAGER' ? 'default' : 'secondary'} className="text-[10px]">
                      {m.role === 'MANAGER' ? 'Менеджер' : 'Участник'}
                    </Badge>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-muted-foreground hover:text-destructive"
                      onClick={() => removeMember.mutate({ teamId: team.id, teamUserId: m.id })}
                    >
                      <UserMinus className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {files && files.length > 0 && (
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">
                Файлы ({files.length})
              </p>
              <div className="space-y-1">
                {files.map((f) => (
                  <a
                    key={f.id}
                    href={f.presignedUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="block text-sm text-primary hover:underline truncate"
                  >
                    {f.filename}
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}

function TeamCard({ team, onClick }: { team: TeamResponse; onClick: () => void }) {
  const activeTeam = useAppStore((s) => s.activeTeam)
  const isActive = activeTeam?.id === team.id

  return (
    <Card className={cn('cursor-pointer active:opacity-70 transition-opacity', isActive && 'border-primary')} onClick={onClick}>
      <CardContent className="p-3 flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{team.chatTitle ?? 'Команда'}</p>
          <p className="text-xs text-muted-foreground">
            {team.kanbanId ? '✅ YouGile подключён' : '⚠️ YouGile не настроен'}
          </p>
        </div>
        {isActive && <Badge variant="default" className="text-[10px]">Активна</Badge>}
        <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
      </CardContent>
    </Card>
  )
}

export function TeamsPage() {
  const { data: myTeams } = useMyTeams()
  const { data: memberTeams } = useMemberOfTeams()
  const [selectedTeam, setSelectedTeam] = useState<TeamResponse | null>(null)

  const allTeams = [...(myTeams ?? []), ...(memberTeams ?? [])]
  const unique = allTeams.filter((t, i, a) => a.findIndex((x) => x.id === t.id) === i)

  return (
    <div className="flex flex-col min-h-full px-4 pt-6 pb-6">
      <div className="mb-4">
        <h1 className="text-xl font-bold">Команды</h1>
      </div>

      {unique.length === 0 && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <p className="text-4xl mb-3">👥</p>
            <p className="text-sm">Нет команд. Создайте или присоединитесь.</p>
          </div>
        </div>
      )}

      {myTeams && myTeams.length > 0 && (
        <div className="mb-4">
          <div className="flex items-center gap-1 mb-2">
            <Crown className="h-3.5 w-3.5 text-muted-foreground" />
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Я менеджер</p>
          </div>
          <div className="space-y-2">
            {myTeams.map((t) => <TeamCard key={t.id} team={t} onClick={() => setSelectedTeam(t)} />)}
          </div>
        </div>
      )}

      {memberTeams && memberTeams.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Я участник</p>
          <div className="space-y-2">
            {memberTeams.map((t) => <TeamCard key={t.id} team={t} onClick={() => setSelectedTeam(t)} />)}
          </div>
        </div>
      )}

      {selectedTeam && (
        <TeamDetailSheet team={selectedTeam} onClose={() => setSelectedTeam(null)} />
      )}
    </div>
  )
}
