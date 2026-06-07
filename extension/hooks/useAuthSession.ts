import { useCallback, useEffect, useRef, useState } from 'react'
import {
  clearAuthSession,
  clearLoginChallenge,
  createLoginChallenge,
  getAuthSession,
  getLoginChallenge,
  pollLoginChallenge,
  watchAuthSession,
  watchLoginChallenge,
} from '../services/auth'
import type { AuthSession, ExtensionLoginChallenge } from '../types/recording'

const POLL_INTERVAL_MS = 2000

export function useAuthSession() {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [challenge, setChallenge] = useState<ExtensionLoginChallenge | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollingRef = useRef<number | null>(null)

  useEffect(() => {
    Promise.all([getAuthSession(), getLoginChallenge()])
      .then(([storedSession, storedChallenge]) => {
        setSession(storedSession)
        setChallenge(storedChallenge)
      })
      .finally(() => setLoading(false))

    const unwatchAuth = watchAuthSession(setSession)
    const unwatchChallenge = watchLoginChallenge(setChallenge)
    return () => {
      unwatchAuth()
      unwatchChallenge()
    }
  }, [])

  useEffect(() => {
    if (pollingRef.current !== null) {
      window.clearInterval(pollingRef.current)
      pollingRef.current = null
    }

    if (!challenge || session) return

    const poll = async () => {
      try {
        const next = await pollLoginChallenge(challenge.code)
        if (next) {
          setSession(next)
          setChallenge(null)
          setError(null)
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
      }
    }

    void poll()
    pollingRef.current = window.setInterval(() => void poll(), POLL_INTERVAL_MS)
    return () => {
      if (pollingRef.current !== null) {
        window.clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [challenge, session])

  const login = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const next = await createLoginChallenge()
      setChallenge(next)
      return null
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e)
      setError(message)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    await clearAuthSession()
    await clearLoginChallenge()
    setSession(null)
    setChallenge(null)
  }, [])

  return { session, challenge, loading, error, login, logout }
}
