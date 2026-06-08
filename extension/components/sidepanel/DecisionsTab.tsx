import { ScrollArea } from '../ui/scroll-area'
import DecisionCard from '../decisions/DecisionCard'
import type { Decision } from '../../types/recording'

interface Props {
  decisions: Decision[]
}

export default function DecisionsTab({ decisions }: Props) {
  if (decisions.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Решения появятся по мере обсуждения...
      </div>
    )
  }

  return (
    <ScrollArea className="h-full px-3 py-2">
      {decisions.map((d) => (
        <DecisionCard key={d.id} decision={d} />
      ))}
    </ScrollArea>
  )
}
