import { Loader2, Check } from 'lucide-react'
import { Progress } from '../ui/progress'
import type { RecordingState } from '../../types/recording'

interface Props {
  state: RecordingState
}

const STEPS = [
  'Получение доступа к вкладке',
  'Создание аудиопотока',
  'Подключение к серверу',
]

export default function StartingScreen({ state }: Props) {
  const step = state.startingStep ?? 0
  const progress = Math.round(((step + 1) / STEPS.length) * 100)

  return (
    <div className="w-[360px] p-4 space-y-4">
      <p className="font-semibold text-sm text-center">Подготовка записи...</p>

      <Progress value={progress} className="h-1.5" />

      <div className="space-y-3">
        {STEPS.map((label, i) => {
          const done = i < step
          const active = i === step
          return (
            <div key={i} className="flex items-center gap-3">
              <div className="flex-shrink-0">
                {done ? (
                  <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                    <Check className="h-3 w-3 text-primary-foreground" />
                  </div>
                ) : active ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                )}
              </div>
              <span className={`text-sm ${active ? 'text-foreground font-medium' : done ? 'text-muted-foreground line-through' : 'text-muted-foreground'}`}>
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
