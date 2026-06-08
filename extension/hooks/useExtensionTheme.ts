import { useCallback, useEffect, useState } from 'react'
import {
  DEFAULT_THEME_PREFERENCE,
  getThemePreference,
  setThemePreference,
  watchThemePreference,
  type ThemePreference,
} from '../services/themeSettings'

const DARK_SCHEME_QUERY = '(prefers-color-scheme: dark)'

function applyThemePreference(preference: ThemePreference): void {
  const systemPrefersDark = window.matchMedia(DARK_SCHEME_QUERY).matches
  const shouldUseDark = preference === 'dark' || (preference === 'system' && systemPrefersDark)

  document.documentElement.classList.toggle('dark', shouldUseDark)
  document.documentElement.style.colorScheme = shouldUseDark ? 'dark' : 'light'
}

export function useExtensionTheme() {
  const [theme, setThemeState] = useState<ThemePreference>(DEFAULT_THEME_PREFERENCE)

  useEffect(() => {
    let mounted = true

    void getThemePreference().then((storedTheme) => {
      if (mounted) {
        setThemeState(storedTheme)
      }
    })

    const unwatchTheme = watchThemePreference(setThemeState)

    return () => {
      mounted = false
      unwatchTheme()
    }
  }, [])

  useEffect(() => {
    const darkScheme = window.matchMedia(DARK_SCHEME_QUERY)
    const applyCurrentTheme = () => applyThemePreference(theme)

    applyCurrentTheme()

    if (theme !== 'system') {
      return undefined
    }

    darkScheme.addEventListener('change', applyCurrentTheme)
    return () => darkScheme.removeEventListener('change', applyCurrentTheme)
  }, [theme])

  const setTheme = useCallback(async (nextTheme: ThemePreference) => {
    setThemeState(nextTheme)
    await setThemePreference(nextTheme)
  }, [])

  return { theme, setTheme }
}
