import { useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useAppStore } from '@/stores/appStore'
import { getColorScheme, getTgUser, tg } from '@/lib/tg'
import { Router } from '@/router'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
})

export default function App() {
  const setTgUser = useAppStore((s) => s.setTgUser)

  useEffect(() => {
    tg?.ready()
    tg?.expand()

    const scheme = getColorScheme()
    if (scheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }

    const user = getTgUser()
    if (user) setTgUser(user)
  }, [setTgUser])

  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      <Toaster position="top-center" richColors />
    </QueryClientProvider>
  )
}
