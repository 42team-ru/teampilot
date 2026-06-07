import { useEffect, useState } from 'react'
import { Progress } from '../ui/progress'

const STEPS = [
  'Транскрипция аудио',
  'Извлечение задач',
  'Генерация summary',
]

export default function ProcessingScreen() {
  const [progress, setProgress] = useState(0)
  const [stepIdx, setStepIdx] = useState(0)

  useEffect(() => {
    const total = 18000 // ~18s fake progress
    const interval = 200
    let elapsed = 0
    const id = setInterval(() => {
      elapsed += interval
      const pct = Math.min(Math.round((elapsed / total) * 100), 95)
      setProgress(pct)
      setStepIdx(pct < 33 ? 0 : pct < 66 ? 1 : 2)
    }, interval)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="w-[360px] p-4 space-y-4">
      <p className="font-semibold text-sm text-center">Обработка встречи</p>

      <Progress value={progress} />

      <div className="space-y-2">
        {STEPS.map((label, i) => (
          <div key={i} className={`flex items-center gap-2 text-sm ${i === stepIdx ? 'text-foreground font-medium' : i < stepIdx ? 'text-muted-foreground' : 'text-muted-foreground/50'}`}>
            <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${i === stepIdx ? 'bg-primary animate-pulse' : i < stepIdx ? 'bg-muted-foreground' : 'bg-muted-foreground/30'}`} />
            {label}
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground text-center">Это может занять до минуты...</p>
    </div>
  )
}
