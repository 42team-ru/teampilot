import { Pause, Square, PanelRight, Mic, MicOff } from 'lucide-react'
import { Button } from '../ui/button'
import { useTimer } from '../../hooks/useTimer'
import { formatDuration, formatBytes, getMeetingPlatform } from '../../lib/utils'
import type { RecordingState } from '../../types/recording'

interface Props {
  state: RecordingState
  onPause: () => void
  onStop: () => void
  onToggleMic: () => void
}

export default function RecordingScreen({ state, onPause, onStop, onToggleMic }: Props) {
  const elapsed = useTimer(state.startedAt, state.totalPausedMs, undefined, true)

  const openPanel = async () => {
    const win = await chrome.windows.getCurrent()
    if (win.id !== undefined) {
      chrome.sidePanel.open({ windowId: win.id }).catch(() => {})
    }
  }

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
