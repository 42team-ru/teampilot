import { useEffect, useState } from 'react'
import { ArrowLeft, Check, LogIn, LogOut, Mic, UserRound } from 'lucide-react'
import { Button } from '../ui/button'
import { ScrollArea } from '../ui/scroll-area'
import { getMicSettings, setMicSettings, listMicrophones } from '../../services/micSettings'
import type { AuthSession } from '../../types/recording'

interface Props {
  onBack: () => void
  authSession?: AuthSession | null
  authLoading?: boolean
  authError?: string | null
  onLogin?: () => void
  onLogout?: () => void
}

export default function SettingsScreen({
  onBack,
  authSession,
  authLoading,
  authError,
  onLogin,
  onLogout,
}: Props) {
  const [mics, setMics] = useState<MediaDeviceInfo[]>([])
  const [selectedId, setSelectedId] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([listMicrophones(), getMicSettings()]).then(([devices, saved]) => {
      setMics(devices)
      setSelectedId(saved?.deviceId ?? devices[0]?.deviceId ?? '')
      setLoading(false)
    })
  }, [])

  const handleSelect = async (device: MediaDeviceInfo) => {
    setSelectedId(device.deviceId)
    await setMicSettings({ deviceId: device.deviceId, label: device.label })
  }

  const micLabel = (device: MediaDeviceInfo) =>
    device.label || `Микрофон ${mics.indexOf(device) + 1}`

  return (
    <div className="w-[360px] flex flex-col" style={{ minHeight: 200 }}>
      <div className="flex items-center gap-2 p-4 border-b">
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onBack}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <span className="font-semibold text-sm">Настройки</span>
      </div>

      <div className="p-4 space-y-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <UserRound className="h-4 w-4 text-muted-foreground" />
            <p className="text-sm font-medium">Telegram аккаунт</p>
          </div>
          <div className="rounded-lg border p-3 space-y-2">
            <p className="text-sm">
              {authSession
                ? `Подключён Telegram ID ${authSession.telegramId}`
                : 'Нужно войти для записи встречи'}
            </p>
            {authError && <p className="text-xs text-destructive">{authError}</p>}
            {authSession ? (
              <Button
                variant="outline"
                size="sm"
                className="w-full gap-1.5"
                onClick={onLogout}
              >
                <LogOut className="h-3.5 w-3.5" />
                Выйти
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="w-full gap-1.5"
                onClick={onLogin}
                disabled={authLoading}
              >
                <LogIn className="h-3.5 w-3.5" />
                Войти через Telegram
              </Button>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Mic className="h-4 w-4 text-muted-foreground" />
          <p className="text-sm font-medium">Микрофон для записи</p>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Загрузка устройств...</p>
        ) : mics.length === 0 ? (
          <p className="text-sm text-muted-foreground">Микрофоны не найдены. Разрешите доступ в браузере.</p>
        ) : (
          <ScrollArea className="max-h-[240px]">
            <div className="space-y-1">
              {mics.map((device) => (
                <button
                  key={device.deviceId}
                  className={`w-full flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm text-left transition-colors ${
                    selectedId === device.deviceId
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  }`}
                  onClick={() => handleSelect(device)}
                >
                  <span className="truncate pr-2">{micLabel(device)}</span>
                  {selectedId === device.deviceId && (
                    <Check className="h-4 w-4 text-primary flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>
    </div>
  )
}
