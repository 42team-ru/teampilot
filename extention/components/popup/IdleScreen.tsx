import { Settings, Radio, Mic, Volume2 } from 'lucide-react'
import { Button } from '../ui/button'
import { useTabInfo } from '../../hooks/useTabInfo'
import { getMeetingPlatform } from '../../lib/utils'

interface Props {
  onStart: () => void
  onOpenSettings: () => void
}

export default function IdleScreen({ onStart, onOpenSettings }: Props) {
  const tab = useTabInfo()

  return (
    <div className="w-[360px] p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm">AI PM Assistant</span>
        </div>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onOpenSettings} title="Настройки">
          <Settings className="h-4 w-4" />
        </Button>
      </div>

      {tab && (
        <div className="rounded-lg border bg-muted/50 p-3 space-y-1">
          <p className="text-xs text-muted-foreground">Текущая вкладка</p>
          <p className="text-sm font-medium truncate">{getMeetingPlatform(tab.url)}</p>
          <p className="text-xs text-muted-foreground truncate">{tab.url}</p>
        </div>
      )}

      <div className="rounded-lg border p-3 space-y-2">
        <p className="text-xs font-medium text-muted-foreground">Что будет записываться</p>
        <div className="flex items-center gap-2 text-sm">
          <Volume2 className="h-3.5 w-3.5 text-green-600" />
          <span>Звук вкладки</span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <Mic className="h-3.5 w-3.5 text-green-600" />
          <span>Микрофон</span>
        </div>
      </div>

      <Button className="w-full" onClick={onStart} disabled={!tab}>
        Начать запись
      </Button>
    </div>
  )
}
