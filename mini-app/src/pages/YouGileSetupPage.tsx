import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { authApi } from '@/api/auth'
import { useAppStore } from '@/stores/appStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'

const loginSchema = z.object({
  login: z.string().email('Введите корректный email'),
  password: z.string().min(1, 'Введите пароль'),
})

type LoginForm = z.infer<typeof loginSchema>

interface Board {
  id: string
  name: string
  token: string
}

export function YouGileSetupPage() {
  const navigate = useNavigate()
  const { setActiveTeam } = useAppStore()
  const [step, setStep] = useState<'auth' | 'board'>('auth')
  const [boards, setBoards] = useState<Board[]>([])
  const [selectedBoard, setSelectedBoard] = useState<string | null>(null)
  const [connecting, setConnecting] = useState(false)
  const [authToken, setAuthToken] = useState('')
  const activeTeam = useAppStore((s) => s.activeTeam)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  })

  const onAuth = async (data: LoginForm) => {
    try {
      const res = await authApi.yougileAuth(data.login, data.password)
      const boardList: Board[] = (res.boards ?? []).map((b: any) => ({
        id: b.id,
        name: b.name,
        token: res.token ?? '',
      }))
      setAuthToken(res.token ?? '')
      setBoards(boardList)
      setStep('board')
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Неверный логин или пароль YouGile')
    }
  }

  const onSelectBoard = async () => {
    if (!selectedBoard || !activeTeam) return
    setConnecting(true)
    try {
      const team = await authApi.yougileSelectBoard(authToken, selectedBoard, activeTeam.id)
      setActiveTeam(team)
      toast.success('YouGile подключён!')
      navigate('/', { replace: true })
    } catch (e: any) {
      toast.error(e?.response?.data?.detail ?? 'Ошибка при выборе доски')
    } finally {
      setConnecting(false)
    }
  }

  if (step === 'board') {
    return (
      <div className="flex flex-col min-h-screen px-6 pt-12 pb-8">
        <div className="mb-2">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-2 h-2 rounded-full bg-muted" />
            <div className="w-2 h-2 rounded-full bg-primary" />
          </div>
          <p className="text-xs text-muted-foreground">Шаг 2 из 2</p>
        </div>

        <h1 className="text-2xl font-bold mb-2 mt-4">Выберите доску</h1>
        <p className="text-muted-foreground text-sm mb-6">Выберите канбан-доску для вашей команды</p>

        <div className="space-y-2 flex-1">
          {boards.map((b) => (
            <button
              key={b.id}
              onClick={() => setSelectedBoard(b.id)}
              className={`w-full text-left rounded-xl border p-4 transition-colors ${
                selectedBoard === b.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border hover:border-muted-foreground'
              }`}
            >
              <p className="text-sm font-medium">{b.name}</p>
            </button>
          ))}
        </div>

        <Button
          className="w-full mt-6"
          disabled={!selectedBoard || connecting}
          onClick={onSelectBoard}
        >
          {connecting ? 'Подключение...' : 'Подключить доску'}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col min-h-screen px-6 pt-12 pb-8">
      <div className="mb-2">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <div className="w-2 h-2 rounded-full bg-muted" />
        </div>
        <p className="text-xs text-muted-foreground">Шаг 1 из 2</p>
      </div>

      <h1 className="text-2xl font-bold mb-2 mt-4">Подключение YouGile</h1>
      <p className="text-muted-foreground text-sm mb-8">Войдите в ваш аккаунт YouGile</p>

      <form onSubmit={handleSubmit(onAuth)} className="space-y-4">
        <div>
          <Input type="email" placeholder="Email" {...register('login')} />
          {errors.login && <p className="text-xs text-destructive mt-1">{errors.login.message}</p>}
        </div>
        <div>
          <Input type="password" placeholder="Пароль" {...register('password')} />
          {errors.password && <p className="text-xs text-destructive mt-1">{errors.password.message}</p>}
        </div>
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Вход...' : 'Войти в YouGile'}
        </Button>
      </form>

      <button
        className="mt-6 text-sm text-muted-foreground text-center w-full"
        onClick={() => navigate('/', { replace: true })}
      >
        Пропустить (настроить позже)
      </button>
    </div>
  )
}
