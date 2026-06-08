export const THEME_PREFERENCES = ['system', 'light', 'dark'] as const

export type ThemePreference = (typeof THEME_PREFERENCES)[number]

export const DEFAULT_THEME_PREFERENCE: ThemePreference = 'system'

const KEY = 'themePreference'

function isThemePreference(value: unknown): value is ThemePreference {
  return (
    typeof value === 'string' &&
    (THEME_PREFERENCES as readonly string[]).includes(value)
  )
}

function normalizeThemePreference(value: unknown): ThemePreference {
  return isThemePreference(value) ? value : DEFAULT_THEME_PREFERENCE
}

export async function getThemePreference(): Promise<ThemePreference> {
  const result = await chrome.storage.local.get(KEY)
  return normalizeThemePreference(result[KEY])
}

export async function setThemePreference(preference: ThemePreference): Promise<void> {
  await chrome.storage.local.set({ [KEY]: preference })
}

export function watchThemePreference(cb: (preference: ThemePreference) => void): () => void {
  const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
    if (KEY in changes) {
      cb(normalizeThemePreference(changes[KEY].newValue))
    }
  }
  chrome.storage.local.onChanged.addListener(handler)
  return () => chrome.storage.local.onChanged.removeListener(handler)
}
