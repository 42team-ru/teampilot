import { useEffect, useRef } from 'react'
import { AlertTriangle, FileText } from 'lucide-react'
import { ScrollArea } from '../ui/scroll-area'
import type { LiveEvent } from '../../types/recording'

interface Props {
  events: LiveEvent[]
}

export default function LiveTab({ events }: Props) {
  const endRef = useRef<HTMLDivElement>(null)
  const displayed = events.slice(-20).reverse()

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [events.length])

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Ожидание событий встречи...
      </div>
    )
  }

  const alerts = events.filter((e) => e.type === 'alert').slice(-3)

  return (
    <div className="flex flex-col h-full">
      {alerts.length > 0 && (
        <div className="px-3 py-2 space-y-1 border-b">
          {alerts.map((e) => (
            <div key={e.id} className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded p-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
              <p className="text-xs text-amber-800">{e.text}</p>
            </div>
          ))}
        </div>
      )}

      <ScrollArea className="flex-1 px-3 py-2">
        <div className="space-y-3">
          {displayed.map((event) => (
            <div key={event.id} className="space-y-0.5">
              <p className="text-xs text-muted-foreground">{event.time}</p>
              {event.type === 'context' ? (
                <div className="flex items-start gap-1.5">
                  <FileText className="h-3 w-3 text-muted-foreground flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground italic leading-relaxed">{event.text}</p>
                </div>
              ) : (
                <p className={`text-sm ${event.type === 'alert' ? 'opacity-60' : ''}`}>{event.text}</p>
              )}
            </div>
          ))}
        </div>
        <div ref={endRef} />
      </ScrollArea>
    </div>
  )
}
