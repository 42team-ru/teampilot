import { useState, useEffect } from 'react'

export interface TabInfo {
  url: string
  title: string
}

export function useTabInfo(): TabInfo | null {
  const [tab, setTab] = useState<TabInfo | null>(null)

  useEffect(() => {
    chrome.tabs.query({ active: true, currentWindow: true }).then((tabs) => {
      const t = tabs[0]
      if (t) setTab({ url: t.url ?? '', title: t.title ?? '' })
    })
  }, [])

  return tab
}
