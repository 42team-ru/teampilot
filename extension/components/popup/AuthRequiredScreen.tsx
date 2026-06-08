import { Copy, ExternalLink, LogIn, Radio } from "lucide-react";
import { Button } from "../ui/button";
import type { ExtensionLoginChallenge } from "../../types/recording";

interface Props {
  loading: boolean;
  challenge?: ExtensionLoginChallenge | null;
  error?: string | null;
  fullHeight?: boolean;
  onLogin: () => void | Promise<unknown>;
}

export default function AuthRequiredScreen({
  loading,
  challenge,
  error,
  fullHeight,
  onLogin,
}: Props) {
  const command = challenge ? `/start ${challenge.code}` : "";
  const botUrl = challenge
    ? `https://t.me/${challenge.botUsername}?start=${challenge.code}`
    : "";

  const copyCommand = () => {
    if (command) navigator.clipboard.writeText(command).catch(() => {});
  };

  return (
    <div
      className={`w-[360px] p-4 space-y-4 ${fullHeight ? "h-screen flex flex-col justify-center" : ""}`}
    >
      <div className="flex items-center gap-2">
        <Radio className="h-5 w-5 text-primary" />
        <span className="font-semibold text-sm">TeamPilot</span>
      </div>

      <div className="rounded-lg border bg-muted/30 p-3 space-y-2">
        <p className="text-sm font-medium">Нужен вход через Telegram</p>
        {challenge ? (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              Откройте бота @{challenge.botUsername} и отправьте команду:
            </p>
            <button
              className="w-full rounded border bg-background px-3 py-2 text-center font-mono text-lg font-semibold"
              onClick={copyCommand}
              title="Скопировать команду"
            >
              {command}
            </button>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 gap-1.5"
                onClick={copyCommand}
              >
                <Copy className="h-3.5 w-3.5" />
                Копировать
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="flex-1 gap-1.5"
                onClick={() => chrome.tabs.create({ url: botUrl })}
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Открыть
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              После сообщения бот подтвердит вход, а расширение войдёт
              автоматически.
            </p>
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Получите одноразовый код и подтвердите его в Telegram-боте.
          </p>
        )}
        {error && <p className="text-xs text-destructive">{error}</p>}
      </div>

      <Button
        className="w-full gap-1.5"
        onClick={() => void onLogin()}
        disabled={loading}
      >
        <LogIn className="h-3.5 w-3.5" />
        {loading
          ? "Проверяем вход..."
          : challenge
            ? "Получить новый код"
            : "Получить код входа"}
      </Button>
    </div>
  );
}
