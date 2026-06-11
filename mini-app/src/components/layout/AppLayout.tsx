import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Kanban, RefreshCw, Users, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { haptic } from '@/lib/tg'

const tabs = [
  { path: '/', label: 'Главная', icon: LayoutDashboard },
  { path: '/board', label: 'Доска', icon: Kanban },
  { path: '/sync', label: 'Дайджест', icon: RefreshCw },
  { path: '/teams', label: 'Команды', icon: Users },
  { path: '/profile', label: 'Профиль', icon: User },
]

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <div className="flex flex-col h-screen bg-background">
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>

      <nav className="border-t bg-background safe-bottom">
        <div className="flex">
          {tabs.map(({ path, label, icon: Icon }) => {
            const active = path === '/' ? location.pathname === '/' : location.pathname.startsWith(path)
            return (
              <button
                key={path}
                onClick={() => {
                  haptic('light')
                  navigate(path)
                }}
                className={cn(
                  'flex-1 flex flex-col items-center gap-0.5 py-2 text-[10px] transition-colors',
                  active ? 'text-primary' : 'text-muted-foreground'
                )}
              >
                <Icon className={cn('h-5 w-5', active && 'stroke-[2.5]')} />
                {label}
              </button>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
