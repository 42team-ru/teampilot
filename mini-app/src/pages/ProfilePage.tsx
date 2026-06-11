import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { usersApi } from '@/api/users'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ChevronRight } from 'lucide-react'
import { getTgUser } from '@/lib/tg'

export function ProfilePage() {
  const { tgUser, logout } = useAppStore()
  const tg = getTgUser() ?? tgUser
  const [achievementsOpen, setAchievementsOpen] = useState(false)

  const { data: stats } = useQuery({
    queryKey: ['user', 'stats', tg?.id],
    queryFn: () => usersApi.getStats(tg!.id),
    enabled: !!tg?.id,
  })

  const initials = tg
    ? `${tg.first_name?.[0] ?? ''}${tg.last_name?.[0] ?? ''}`.toUpperCase() || '?'
    : '?'

  const xpProgress = stats
    ? stats.xpForNextLevel > stats.xpForCurrentLevel
      ? Math.round(
          ((stats.xp - stats.xpForCurrentLevel) /
            (stats.xpForNextLevel - stats.xpForCurrentLevel)) *
            100
        )
      : 100
    : 0

  const earnedAchievements = stats?.achievements.filter((a) => a.awardedAt) ?? []
  const lockedAchievements = stats?.achievements.filter((a) => !a.awardedAt) ?? []

  return (
    <div className="flex flex-col min-h-full px-4 pt-6 pb-6 gap-4">
      <h1 className="text-xl font-bold">Профиль</h1>

      {/* Avatar + name */}
      <div className="flex flex-col items-center">
        <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center text-2xl font-bold text-primary mb-3 overflow-hidden">
          {tg?.photo_url ? (
            <img src={tg.photo_url} alt="avatar" className="w-full h-full object-cover" />
          ) : (
            initials
          )}
        </div>
        <p className="text-lg font-semibold">
          {tg?.first_name} {tg?.last_name}
        </p>
        {tg?.username && <p className="text-sm text-muted-foreground">@{tg.username}</p>}
      </div>

      {stats && (
        <>
          {/* Level + XP */}
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Уровень {stats.level}</p>
                  <p className="text-base font-semibold">{stats.levelName}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">XP</p>
                  <p className="text-base font-semibold">{stats.xp.toLocaleString()}</p>
                </div>
              </div>
              <div className="w-full bg-muted rounded-full h-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
                  style={{ width: `${xpProgress}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.xp - stats.xpForCurrentLevel} / {stats.xpForNextLevel - stats.xpForCurrentLevel} XP до следующего уровня
              </p>
            </CardContent>
          </Card>

          {/* Stats grid */}
          <Card>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Статистика</p>
              <div className="grid grid-cols-2 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold">{stats.completedCount}</p>
                  <p className="text-xs text-muted-foreground">Завершено задач</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.streakDays} 🔥</p>
                  <p className="text-xs text-muted-foreground">Дней подряд</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{Math.round(stats.onTimeRate * 100)}%</p>
                  <p className="text-xs text-muted-foreground">В срок</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.overdueCount}</p>
                  <p className="text-xs text-muted-foreground">Просрочено</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Achievements */}
          {(earnedAchievements.length > 0 || lockedAchievements.length > 0) && (
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">
                    Достижения ({earnedAchievements.length}/{stats.achievements.length})
                  </p>
                  <button
                    onClick={() => setAchievementsOpen(true)}
                    className="flex items-center gap-1 text-xs text-primary"
                  >
                    Посмотреть все <ChevronRight className="h-3 w-3" />
                  </button>
                </div>
                <div className="space-y-2">
                  {earnedAchievements.map((a) => (
                    <div key={a.key} className="flex items-center gap-3">
                      <span className="text-2xl">{a.emoji}</span>
                      <div>
                        <p className="text-sm font-medium">{a.name}</p>
                        {a.awardedAt && (
                          <p className="text-xs text-muted-foreground">
                            {new Date(a.awardedAt).toLocaleDateString('ru-RU')}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                  {lockedAchievements.map((a) => (
                    <div key={a.key} className="flex items-center gap-3 opacity-40">
                      <span className="text-2xl grayscale">{a.emoji}</span>
                      <p className="text-sm">{a.name}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Achievements full-screen sheet */}
          <Sheet open={achievementsOpen} onOpenChange={setAchievementsOpen}>
            <SheetContent side="bottom" className="pb-8 max-h-[85vh] overflow-y-auto">
              <SheetHeader className="pt-4">
                <SheetTitle>Достижения</SheetTitle>
              </SheetHeader>
              <div className="px-4 mt-4 space-y-3">
                {earnedAchievements.map((a) => (
                  <div key={a.key} className="flex items-center gap-3">
                    <span className="text-2xl">{a.emoji}</span>
                    <div>
                      <p className="text-sm font-medium">{a.name}</p>
                      {a.awardedAt && (
                        <p className="text-xs text-muted-foreground">
                          {new Date(a.awardedAt).toLocaleDateString('ru-RU')}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                {lockedAchievements.map((a) => (
                  <div key={a.key} className="flex items-center gap-3 opacity-40">
                    <span className="text-2xl grayscale">{a.emoji}</span>
                    <div>
                      <p className="text-sm">{a.name}</p>
                      <p className="text-xs text-muted-foreground">Не получено</p>
                    </div>
                  </div>
                ))}
              </div>
            </SheetContent>
          </Sheet>
        </>
      )}

      <div className="mt-auto pt-2">
        <Button variant="outline" className="w-full text-destructive hover:text-destructive" onClick={logout}>
          Выйти
        </Button>
      </div>
    </div>
  )
}
