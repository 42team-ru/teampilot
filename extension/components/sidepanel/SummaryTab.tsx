import { Copy, Send, Save } from 'lucide-react'
import { ScrollArea } from '../ui/scroll-area'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import type { Summary } from '../../types/recording'

interface Props {
  summary: Summary | undefined
  meetingId?: string
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{title}</p>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm flex gap-2">
            <span className="text-muted-foreground flex-shrink-0">·</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

export default function SummaryTab({ summary }: Props) {
  if (!summary) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Summary появится после обработки встречи
      </div>
    )
  }

  const summaryText = [
    `Цель: ${summary.goal}`,
    summary.topics.length > 0 ? `\nТемы:\n${summary.topics.map((t) => `• ${t}`).join('\n')}` : '',
    summary.decisions.length > 0 ? `\nРешения:\n${summary.decisions.map((d) => `• ${d}`).join('\n')}` : '',
    summary.risks.length > 0 ? `\nРиски:\n${summary.risks.map((r) => `• ${r}`).join('\n')}` : '',
    summary.nextSteps.length > 0 ? `\nСледующие шаги:\n${summary.nextSteps.map((s) => `• ${s}`).join('\n')}` : '',
  ]
    .filter(Boolean)
    .join('')

  const handleCopy = () => {
    navigator.clipboard.writeText(summaryText).catch(() => {})
  }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1 px-3 py-2">
        <div className="space-y-4">
          {summary.goal && (
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Цель встречи</p>
              <p className="text-sm mt-1">{summary.goal}</p>
            </div>
          )}
          <Section title="Основные темы" items={summary.topics} />
          <Section title="Решения" items={summary.decisions} />
          <Section title="Риски" items={summary.risks} />
          <Section title="Следующие шаги" items={summary.nextSteps} />
        </div>
      </ScrollArea>

      <Separator />
      <div className="flex gap-2 p-3">
        <Button size="sm" variant="outline" className="flex-1 text-xs" onClick={handleCopy}>
          <Copy className="h-3 w-3 mr-1" /> Скопировать
        </Button>
        <Button size="sm" variant="outline" className="flex-1 text-xs" disabled>
          <Send className="h-3 w-3 mr-1" /> Telegram
        </Button>
        <Button size="sm" variant="outline" className="flex-1 text-xs" disabled>
          <Save className="h-3 w-3 mr-1" /> Сохранить
        </Button>
      </div>
    </div>
  )
}
