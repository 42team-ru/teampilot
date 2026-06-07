import { useState, useEffect, useRef } from 'react'
import { Pause, Square, PanelRight, Mic, MicOff, Download, Loader2 } from 'lucide-react'
import { Button } from '../ui/button'
import { useTimer } from '../../hooks/useTimer'
import { formatDuration, formatBytes, getMeetingPlatform } from '../../lib/utils'
import type { RecordingState } from '../../types/recording'
import type { ExtMessage } from '../../types/messages'

interface Props {
  state: RecordingState
  onPause: () => void
  onStop: () => void
  onToggleMic: () => void
}

export default function RecordingScreen({ state, onPause, onStop, onToggleMic }: Props) {
  const elapsed = useTimer(state.startedAt, state.totalPausedMs, undefined, true)
  const [audioLevel, setAudioLevel] = useState(0)
  const [testLoading, setTestLoading] = useState(false)
  const [testError, setTestError] = useState<string | null>(null)
  const levelHistoryRef = useRef<number[]>(Array(20).fill(0))

  useEffect(() => {
    // Offscreen can only message the service worker directly, so levels are relayed
    // via chrome.storage.session. Watch it for real-time updates.
    chrome.storage.session.get(['audioLevel'], (data) => {
      if (typeof data.audioLevel === 'number') {
        setAudioLevel(data.audioLevel)
        levelHistoryRef.current = [...levelHistoryRef.current.slice(1), data.audioLevel]
      }
    })

    const storageListener = (
      changes: Record<string, chrome.storage.StorageChange>,
      area: string,
    ) => {
      if (area !== 'session' || !('audioLevel' in changes)) return
      const level = changes.audioLevel.newValue as number
      setAudioLevel(level)
      levelHistoryRef.current = [...levelHistoryRef.current.slice(1), level]
    }
    chrome.storage.onChanged.addListener(storageListener)
    return () => chrome.storage.onChanged.removeListener(storageListener)
  }, [])

  const openPanel = async () => {
    const win = await chrome.windows.getCurrent()
    if (win.id !== undefined) {
      chrome.sidePanel.open({ windowId: win.id }).catch(() => {})
    }
  }

  const handleTestAudio = async () => {
    setTestLoading(true)
    setTestError(null)
    try {
      const response = (await chrome.runtime.sendMessage({
        type: 'REQUEST_TEST_AUDIO',
      } as ExtMessage)) as { bytes?: number[]; contentType?: string; error?: string } | undefined

      if (response?.error) {
        setTestError(response.error)
        return
      }
      if (!response?.bytes?.length) {
        setTestError('Получен пустой аудиофайл — звук не захватывается')
        return
      }

      const blob = new Blob([new Uint8Array(response.bytes)], {
        type: response.contentType ?? 'audio/webm',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'audio-test-5s.webm'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 15_000)
    } catch (e) {
      setTestError('Ошибка теста: ' + String(e))
    } finally {
      setTestLoading(false)
    }
  }

  const levelBars = levelHistoryRef.current
  const isActive = audioLevel > 2

  return (
    <div className="w-[360px] p-4 space-y-4">
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-2.5 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
        <span className="font-semibold text-sm">Запись идёт</span>
        {state.tabUrl && (
          <span className="text-xs text-muted-foreground ml-auto truncate max-w-[140px]">
            {getMeetingPlatform(state.tabUrl)}
          </span>
        )}
      </div>

      <div className="rounded-lg border bg-muted/30 p-3">
        <p className="text-2xl font-mono font-bold text-center">{formatDuration(elapsed)}</p>
      </div>

      {/* Audio level indicator */}
      <div className="rounded-lg border p-3 space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Уровень аудио</span>
          <span className={isActive ? 'text-green-500 font-medium' : 'text-yellow-500 font-medium'}>
            {isActive ? 'Звук есть' : 'Тихо / нет звука'}
          </span>
        </div>
        <div className="flex items-end gap-0.5 h-6">
          {levelBars.map((lvl, i) => (
            <div
              key={i}
              className="flex-1 rounded-sm transition-all duration-150"
              style={{
                height: `${Math.max(10, lvl)}%`,
                backgroundColor: lvl > 30 ? '#22c55e' : lvl > 5 ? '#eab308' : '#e5e7eb',
              }}
            />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded border p-2 text-center">
          <p className="text-muted-foreground">Чанков</p>
          <p className="font-semibold text-base">{state.chunks}</p>
        </div>
        <div className="rounded border p-2 text-center">
          <p className="text-muted-foreground">Размер</p>
          <p className="font-semibold text-base">{formatBytes(state.bytes)}</p>
        </div>
      </div>

      <div className="flex items-center justify-between rounded-lg border px-3 py-2">
        <span className="text-xs text-muted-foreground">Микрофон</span>
        <Button
          variant={state.micMuted ? 'destructive' : 'outline'}
          size="sm"
          className="h-7 gap-1.5 text-xs"
          onClick={onToggleMic}
        >
          {state.micMuted ? (
            <><MicOff className="h-3.5 w-3.5" /> Выкл</>
          ) : (
            <><Mic className="h-3.5 w-3.5" /> Вкл</>
          )}
        </Button>
      </div>

      {/* Test audio download */}
      <div className="rounded-lg border px-3 py-2 space-y-1.5">
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground">Тест захвата звука (5 сек)</span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 gap-1.5 text-xs"
            onClick={handleTestAudio}
            disabled={testLoading}
          >
            {testLoading ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Запись…</>
            ) : (
              <><Download className="h-3.5 w-3.5" /> Скачать</>
            )}
          </Button>
        </div>
        {testError && (
          <p className="text-xs text-destructive">{testError}</p>
        )}
      </div>

      <div className="flex gap-2">
        <Button variant="outline" size="sm" className="flex-1" onClick={onPause}>
          <Pause className="h-3.5 w-3.5 mr-1" /> Пауза
        </Button>
        <Button variant="outline" size="sm" className="flex-1" onClick={openPanel}>
          <PanelRight className="h-3.5 w-3.5 mr-1" /> Панель
        </Button>
        <Button variant="destructive" size="sm" className="flex-1" onClick={onStop}>
          <Square className="h-3.5 w-3.5 mr-1" /> Стоп
        </Button>
      </div>
    </div>
  )
}
