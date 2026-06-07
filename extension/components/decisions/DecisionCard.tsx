import { CheckCircle2 } from 'lucide-react'
import type { Decision } from '../../types/recording'

interface Props {
  decision: Decision
}

export default function DecisionCard({ decision }: Props) {
  return (
    <div className="flex gap-3 p-3 rounded-lg border bg-card mb-2">
      <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm">{decision.text}</p>
        {decision.timestamp && (
          <p className="text-xs text-muted-foreground mt-1">{decision.timestamp}</p>
        )}
      </div>
    </div>
  )
}
