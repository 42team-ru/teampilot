import { Pause, Play, Square, Mic, MicOff, Settings } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { useTimer } from "../../hooks/useTimer";
import { formatDuration, getMeetingPlatform } from "../../lib/utils";
import type { RecordingState } from "../../types/recording";

interface Props {
  state: RecordingState;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onToggleMic: () => void;
  onOpenSettings: () => void;
  onReset?: () => void;
}

const STATUS_CONFIG = {
  idle: { label: "Не записываем", variant: "secondary" as const },
  starting: { label: "Подготовка...", variant: "warning" as const },
  recording: { label: "Запись", variant: "destructive" as const },
  paused: { label: "Пауза", variant: "warning" as const },
  processing: { label: "Обработка", variant: "info" as const },
  error: { label: "Ошибка", variant: "destructive" as const },
  done: { label: "Завершено", variant: "success" as const },
};

export default function SidePanelHeader({
  state,
  onPause,
  onResume,
  onStop,
  onToggleMic,
  onOpenSettings,
  onReset,
}: Props) {
  const elapsed = useTimer(
    state.startedAt,
    state.totalPausedMs,
    state.pausedAt,
    state.status === "recording",
  );
  const { label, variant } = STATUS_CONFIG[state.status] ?? STATUS_CONFIG.idle;
  const isActive = state.status === "recording" || state.status === "paused";

  return (
    <div className="border-b px-3 py-2 space-y-2">
      {/* Row 1: title + status + settings */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {state.status === "recording" && (
            <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse flex-shrink-0" />
          )}
          <span className="font-semibold text-sm">TeamPilot</span>
        </div>
        <div className="flex items-center gap-1">
          <Badge variant={variant} className="text-xs">
            {label}
          </Badge>
          <Button
            size="icon"
            variant="ghost"
            className="h-6 w-6"
            onClick={onOpenSettings}
            title="Настройки"
          >
            <Settings className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Row 2: meeting info + controls */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          {state.tabUrl && (
            <p className="text-xs text-muted-foreground">
              {getMeetingPlatform(state.tabUrl)}
            </p>
          )}
          {isActive && (
            <p className="text-sm font-mono font-medium">
              {formatDuration(elapsed)}
            </p>
          )}
        </div>

        {isActive && (
          <div className="flex gap-1">
            {/* Mic toggle */}
            <Button
              size="icon"
              variant={state.micMuted ? "destructive" : "outline"}
              className="h-7 w-7"
              onClick={onToggleMic}
              title={
                state.micMuted ? "Включить микрофон" : "Выключить микрофон"
              }
            >
              {state.micMuted ? (
                <MicOff className="h-3.5 w-3.5" />
              ) : (
                <Mic className="h-3.5 w-3.5" />
              )}
            </Button>

            {/* Pause / Resume */}
            {state.status === "recording" ? (
              <Button
                size="icon"
                variant="outline"
                className="h-7 w-7"
                onClick={onPause}
                title="Пауза"
              >
                <Pause className="h-3.5 w-3.5" />
              </Button>
            ) : (
              <Button
                size="icon"
                variant="outline"
                className="h-7 w-7"
                onClick={onResume}
                title="Продолжить"
              >
                <Play className="h-3.5 w-3.5" />
              </Button>
            )}

            {/* Stop */}
            <Button
              size="icon"
              variant="destructive"
              className="h-7 w-7"
              onClick={onStop}
              title="Остановить"
            >
              <Square className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {state.status === "done" && onReset && (
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs"
            onClick={onReset}
          >
            Начать заново
          </Button>
        )}
      </div>
    </div>
  );
}
