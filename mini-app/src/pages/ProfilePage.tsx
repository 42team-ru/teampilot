import { useQuery } from '@tanstack/react-query'
import { useAppStore } from '@/stores/appStore'
import { usersApi } from '@/api/users'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { getTgUser } from '@/lib/tg'

export function ProfilePage() {
  const { tgUser, logout } = useAppStore()
  const tg = getTgUser() ?? tgUser

  const { data: stats } = useQuery({
    queryKey: ['user', 'stats', tg?.id],
    queryFn: () => usersApi.getStats(tg!.id),
    enabled: !!tg?.id,
  })

  const initials = tg
    ? `${tg.first_name?.[0] ?? ''}${tg.last_name?.[0] ?? ''}`.toUpperCase() || '?'
    : '?'

  return (
    <div className="flex flex-col min-h-full px-4 pt-6 pb-6">
      <h1 className="text-xl font-bold mb-6">Профиль</h1>

      <div className="flex flex-col items-center mb-6">
        <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center text-2xl font-bold text-primary mb-3">
          {tg?.photo_url ? (
            <img src={tg.photo_url} alt="avatar" className="w-full h-full rounded-full object-cover" />
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
        <Card className="mb-4">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Статистика</p>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xl font-bold">{(stats as any).completedTasksCount ?? 0}</p>
                <p className="text-xs text-muted-foreground">Завершено</p>
              </div>
              <div>
                <p className="text-xl font-bold">{(stats as any).activeTasksCount ?? 0}</p>
                <p className="text-xs text-muted-foreground">Активных</p>
              </div>
              <div>
                <p className="text-xl font-bold">{(stats as any).points ?? 0}</p>
                <p className="text-xs text-muted-foreground">Очки</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="mt-auto">
        <Button variant="outline" className="w-full text-destructive hover:text-destructive" onClick={logout}>
          Выйти
        </Button>
      </div>
    </div>
  )
}
