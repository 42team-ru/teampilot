import { Play, Square } from 'lucide-react'
import { Button } from '../ui/button'
import type { RecordingState } from '../../types/recording'

interface Props {
  state: RecordingState
  onResume: () => void
  onStop: () => void
}

export default function PausedScreen({ onResume, onStop }: Props) {
  return (
    <div className="w-[360px] p-4 space-y-4">
      <div className="flex items-center gap-2 justify-center">
        <span className="text-2xl">⏸</span>
        <span className="font-semibold text-sm">Запись приостановлена</span>
      </div>

      <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-center">
        <p className="text-sm text-yellow-800">Аудио не записывается</p>
      </div>

      <div className="flex gap-2">
        <Button className="flex-1" onClick={onResume}>
          <Play className="h-3.5 w-3.5 mr-1" /> Продолжить
        </Button>
        <Button variant="destructive" className="flex-1" onClick={onStop}>
          <Square className="h-3.5 w-3.5 mr-1" /> Завершить
        </Button>
      </div>
    </div>
  )
}
