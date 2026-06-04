import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '../ui/button'

interface Props {
  error: string
  onRetry: () => void
}

export default function ErrorScreen({ error, onRetry }: Props) {
  return (
    <div className="w-[360px] p-4 space-y-4">
      <div className="flex items-center gap-2 text-destructive">
        <AlertCircle className="h-5 w-5 flex-shrink-0" />
        <span className="font-semibold text-sm">Ошибка записи</span>
      </div>

      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3">
        <p className="text-sm text-destructive break-words">{error}</p>
      </div>

      <Button className="w-full" onClick={onRetry}>
        <RefreshCw className="h-3.5 w-3.5 mr-2" /> Повторить
      </Button>
    </div>
  )
}
