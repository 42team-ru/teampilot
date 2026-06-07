const DEFAULT_API_BASE_URL = 'http://localhost:8080'
const DEFAULT_TELEGRAM_BOT_USERNAME = 'prorab_bot'

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, '')
}

export function getApiBaseUrl(): string {
  return stripTrailingSlash(import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL)
}

export function getWebSocketUrl(): string {
  const configured = import.meta.env.VITE_WS_URL
  if (configured) return configured

  const apiBase = getApiBaseUrl()
  const wsBase = apiBase.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
  return `${wsBase}/ws`
}

export function getTelegramBotUsername(): string {
  return import.meta.env.VITE_TELEGRAM_BOT_USERNAME || DEFAULT_TELEGRAM_BOT_USERNAME
}
