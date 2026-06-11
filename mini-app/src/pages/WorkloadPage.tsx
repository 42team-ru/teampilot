import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, CheckCircle2, ClipboardList, Eye, Gauge, Users } from 'lucide-react'
import { useMyTeams, useTeamWorkload } from '@/hooks/useTeams'
import { useAppStore } from '@/stores/appStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { haptic } from '@/lib/tg'
import type { TeamWorkloadEntry } from '@/api/types'

const THRESHOLDS = { ok: 5, overloaded: 9 } as const

type WorkloadStatus = 'free' | 'normal' | 'overloaded'

const statusConfig: Record<
  WorkloadStatus,
  {
    label: string
    badge: 'success' | 'warning' | 'destructive'
    barClassName: string
    textClassName: string
  }
> = {
  free: {
    label: 'Свободен',
    badge: 'success',
    barClassName: 'bg-green-500',
    textClassName: 'text-green-700 dark:text-green-400',
  },
  normal: {
    label: 'В норме',
    badge: 'warning',
    barClassName: 'bg-yellow-500',
    textClassName: 'text-yellow-700 dark:text-yellow-400',
  },
  overloaded: {
    label: 'Перегружен',
    badge: 'destructive',
    barClassName: 'bg-destructive',
    textClassName: 'text-destructive',
  },
}

function getMemberName(entry: TeamWorkloadEntry) {
  const fullName = [entry.firstName, entry.lastName].filter(Boolean).join(' ')
  return fullName || entry.telegramLogin || String(entry.telegramId)
}

function getMemberInitial(entry: TeamWorkloadEntry) {
  return getMemberName(entry).trim().charAt(0).toUpperCase() || '?'
}

function getStatus(openTaskCount: number): WorkloadStatus {
  if (openTaskCount >= THRESHOLDS.overloaded) return 'overloaded'
  if (openTaskCount >= THRESHOLDS.ok) return 'normal'
  return 'free'
}

function WorkloadSkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3].map((item) => (
        <div key={item} className="rounded-xl border bg-card p-4 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-muted" />
            <div className="flex-1 space-y-2">
              <div className="h-3 w-32 rounded bg-muted" />
              <div className="h-2 w-full rounded bg-muted" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export function WorkloadPage() {
  const navigate = useNavigate()
  const activeTeam = useAppStore((s) => s.activeTeam)
  const { data: managerTeams, isLoading: isManagerTeamsLoading } = useMyTeams()

  const isActiveTeamManaged = !!activeTeam && !!managerTeams?.some((team) => team.id === activeTeam.id)
  const { data: workload, isLoading: isWorkloadLoading } = useTeamWorkload(
    isActiveTeamManaged ? activeTeam.id : undefined
  )

  const sortedWorkload = useMemo(
    () =>
      [...(workload ?? [])].sort(
        (a, b) => b.openTaskCount - a.openTaskCount || b.overdueTaskCount - a.overdueTaskCount
      ),
    [workload]
  )

  const totalTasks = sortedWorkload.reduce((sum, member) => sum + member.openTaskCount, 0)
  const overloadedCount = sortedWorkload.filter(
    (member) => getStatus(member.openTaskCount) === 'overloaded'
  ).length
  const freeCount = sortedWorkload.filter((member) => getStatus(member.openTaskCount) === 'free').length

  const openBoardForMember = (teamUserId: string) => {
    haptic('light')
    navigate(`/board?assignee=${teamUserId}`)
  }

  if (!activeTeam) {
    return (
      <div className="flex min-h-full flex-col px-4 pt-6 pb-6">
        <h1 className="text-xl font-bold">Нагрузка команды</h1>
        <div className="flex flex-1 items-center justify-center text-center">
          <div>
            <Users className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Выберите активную команду, чтобы увидеть нагрузку.</p>
            <Button className="mt-4" size="sm" onClick={() => navigate('/teams')}>
              К командам
            </Button>
          </div>
        </div>
      </div>
    )
  }

  if (!isManagerTeamsLoading && !isActiveTeamManaged) {
    return (
      <div className="flex min-h-full flex-col px-4 pt-6 pb-6">
        <h1 className="text-xl font-bold">Нагрузка команды</h1>
        <div className="flex flex-1 items-center justify-center text-center">
          <div>
            <Gauge className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-sm font-medium">Доступно менеджеру активной команды</p>
            <p className="mt-1 text-xs text-muted-foreground">
              Переключитесь на команду, где вы менеджер.
            </p>
            <Button className="mt-4" size="sm" variant="outline" onClick={() => navigate('/teams')}>
              Выбрать команду
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-full flex-col px-4 pt-6 pb-6">
      <div className="mb-4">
        <h1 className="text-xl font-bold">Нагрузка команды</h1>
        <p className="mt-1 text-sm text-muted-foreground truncate">
          {activeTeam.chatTitle ?? 'Активная команда'}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2 pb-4">
        <div className="rounded-xl border bg-card p-3">
          <ClipboardList className="mb-2 h-4 w-4 text-muted-foreground" />
          <p className="text-lg font-bold">{totalTasks}</p>
          <p className="text-[10px] leading-tight text-muted-foreground">Всего задач</p>
        </div>
        <div className="rounded-xl border bg-card p-3">
          <AlertTriangle className="mb-2 h-4 w-4 text-destructive" />
          <p className="text-lg font-bold text-destructive">{overloadedCount}</p>
          <p className="text-[10px] leading-tight text-muted-foreground">Перегружены</p>
        </div>
        <div className="rounded-xl border bg-card p-3">
          <CheckCircle2 className="mb-2 h-4 w-4 text-green-600 dark:text-green-400" />
          <p className="text-lg font-bold text-green-700 dark:text-green-400">{freeCount}</p>
          <p className="text-[10px] leading-tight text-muted-foreground">Свободны</p>
        </div>
      </div>

      {(isManagerTeamsLoading || isWorkloadLoading) && <WorkloadSkeleton />}

      {!isManagerTeamsLoading && !isWorkloadLoading && sortedWorkload.length === 0 && (
        <div className="flex flex-1 items-center justify-center text-center">
          <div>
            <ClipboardList className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">Нет участников с открытыми задачами.</p>
          </div>
        </div>
      )}

      {!isWorkloadLoading && sortedWorkload.length > 0 && (
        <div className="space-y-3">
          {sortedWorkload.map((member) => {
            const status = getStatus(member.openTaskCount)
            const config = statusConfig[status]
            const progress = Math.min(100, Math.round((member.openTaskCount / THRESHOLDS.overloaded) * 100))

            return (
              <div key={member.teamUserId} className="rounded-xl border bg-card p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold">
                    {getMemberInitial(member)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold">{getMemberName(member)}</p>
                        {member.telegramLogin && (
                          <p className="truncate text-xs text-muted-foreground">@{member.telegramLogin}</p>
                        )}
                      </div>
                      <Badge variant={config.badge} className="flex-shrink-0 text-[10px]">
                        {config.label}
                      </Badge>
                    </div>

                    <div className="mt-3">
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Открытые задачи</span>
                        <span className={cn('font-bold', config.textClassName)}>{member.openTaskCount}</span>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn('h-full rounded-full transition-all', config.barClassName)}
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-between gap-3">
                      <span
                        className={cn(
                          'text-xs font-medium',
                          member.overdueTaskCount > 0 ? 'text-destructive' : 'text-muted-foreground'
                        )}
                      >
                        Просрочено: {member.overdueTaskCount}
                      </span>
                      <Button size="sm" variant="outline" onClick={() => openBoardForMember(member.teamUserId)}>
                        <Eye className="mr-1 h-3.5 w-3.5" />
                        Задачи
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
