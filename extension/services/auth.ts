import { getApiBaseUrl, getTelegramBotUsername } from './config'
import type {
  AuthSession,
  ExtensionLoginChallenge,
  ExtensionLoginStartResponse,
  ExtensionLoginStatusResponse,
} from '../types/recording'

const AUTH_KEY = 'authSession'
const CHALLENGE_KEY = 'extensionLoginChallenge'

export async function getAuthSession(): Promise<AuthSession | null> {
  const result = await chrome.storage.local.get(AUTH_KEY)
  return (result[AUTH_KEY] as AuthSession | undefined) ?? null
}

export async function setAuthSession(session: AuthSession): Promise<void> {
  await chrome.storage.local.set({ [AUTH_KEY]: session })
}

export async function clearAuthSession(): Promise<void> {
  await chrome.storage.local.remove(AUTH_KEY)
}

export function watchAuthSession(cb: (session: AuthSession | null) => void): () => void {
  const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
    if (AUTH_KEY in changes) {
      cb((changes[AUTH_KEY].newValue as AuthSession | undefined) ?? null)
    }
  }
  chrome.storage.local.onChanged.addListener(handler)
  return () => chrome.storage.local.onChanged.removeListener(handler)
}

export async function requireAuthSession(): Promise<AuthSession> {
  const session = await getAuthSession()
  if (!session?.token) {
    throw new Error('Войдите через Telegram перед началом записи')
  }
  return session
}

export async function getLoginChallenge(): Promise<ExtensionLoginChallenge | null> {
  const result = await chrome.storage.local.get(CHALLENGE_KEY)
  const challenge = (result[CHALLENGE_KEY] as ExtensionLoginChallenge | undefined) ?? null
  if (!challenge) return null
  if (new Date(challenge.expiresAt).getTime() <= Date.now()) {
    await clearLoginChallenge()
    return null
  }
  return challenge
}

export async function clearLoginChallenge(): Promise<void> {
  await chrome.storage.local.remove(CHALLENGE_KEY)
}

export function watchLoginChallenge(
  cb: (challenge: ExtensionLoginChallenge | null) => void
): () => void {
  const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
    if (CHALLENGE_KEY in changes) {
      cb((changes[CHALLENGE_KEY].newValue as ExtensionLoginChallenge | undefined) ?? null)
    }
  }
  chrome.storage.local.onChanged.addListener(handler)
  return () => chrome.storage.local.onChanged.removeListener(handler)
}

export async function createLoginChallenge(): Promise<ExtensionLoginChallenge> {
  const response = await fetch(`${getApiBaseUrl()}/auth/extension-login`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  })

  if (!response.ok) {
    throw new Error(await readBackendError(response))
  }

  const data = (await response.json()) as ExtensionLoginStartResponse
  const challenge: ExtensionLoginChallenge = {
    code: data.code,
    expiresAt: data.expiresAt,
    botUsername: getTelegramBotUsername(),
  }
  await chrome.storage.local.set({ [CHALLENGE_KEY]: challenge })
  return challenge
}

export async function pollLoginChallenge(code: string): Promise<AuthSession | null> {
  const response = await fetch(`${getApiBaseUrl()}/auth/extension-login/${encodeURIComponent(code)}`, {
    headers: { 'Accept': 'application/json' },
  })

  if (!response.ok) {
    throw new Error(await readBackendError(response))
  }

  const status = (await response.json()) as ExtensionLoginStatusResponse
  if (status.status === 'expired') {
    await clearLoginChallenge()
    throw new Error('Код входа истёк. Получите новый код.')
  }
  if (status.status !== 'confirmed' || !status.auth) {
    return null
  }

  await setAuthSession(status.auth)
  await clearLoginChallenge()
  return status.auth
}

async function readBackendError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    if (typeof data?.message === 'string') return data.message
    if (typeof data?.title === 'string') return data.title
  } catch {
    // fall through to status text
  }
  return response.statusText || `HTTP ${response.status}`
}
