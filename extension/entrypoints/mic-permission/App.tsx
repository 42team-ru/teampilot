import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, Loader2, Mic, RefreshCw } from 'lucide-react'
import { Button } from '../../components/ui/button'
import { useExtensionTheme } from '../../hooks/useExtensionTheme'
import type { ExtMessage } from '../../types/messages'

type PermissionStatus = 'requesting' | 'granted' | 'failed'

export default function App() {
  useExtensionTheme()

  const [status, setStatus] = useState<PermissionStatus>('requesting')
  const [error, setError] = useState<string | null>(null)

  const closeWindow = useCallback(() => {
    window.setTimeout(() => {
      window.close()
    }, 250)
  }, [])

  const requestPermission = useCallback(async () => {
    setStatus('requesting')
    setError(null)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      stream.getTracks().forEach((track) => track.stop())
      setStatus('granted')

      await chrome.runtime
        .sendMessage({ type: 'MIC_PERMISSION_GRANTED' } satisfies ExtMessage)
        .catch(() => {})

      closeWindow()
    } catch (err) {
      setStatus('failed')
      setError(err instanceof Error ? err.message : String(err))
    }
  }, [closeWindow])

  useEffect(() => {
    void requestPermission()
  }, [requestPermission])

  return (
    <div className="min-h-screen bg-background px-4 py-6 flex items-center justify-center">
      <div className="w-full max-w-sm rounded-lg border bg-card p-5 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Mic className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">Доступ к микрофону</span>
        </div>

        <div className="space-y-2">
          {status === 'requesting' && (
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Запрашиваем разрешение...
            </p>
          )}
          {status === 'granted' && (
            <p className="text-sm text-green-600 flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Разрешение получено. Возвращаемся в расширение...
            </p>
          )}
          {status === 'failed' && (
            <p className="text-sm text-muted-foreground">
              Chrome не выдал разрешение автоматически, нажмите повторно.
            </p>
          )}
        </div>

        {error && (
          <p className="text-sm text-destructive break-words">{error}</p>
        )}

        {status === 'failed' && (
          <Button className="w-full gap-2" onClick={() => void requestPermission()}>
            <RefreshCw className="h-4 w-4" />
            Повторить
          </Button>
        )}
      </div>
    </div>
  )
}
