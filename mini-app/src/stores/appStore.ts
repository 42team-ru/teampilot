import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { TeamResponse } from '@/api/types'

interface TgUser {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
}

interface AppState {
  jwt: string | null
  tgUser: TgUser | null
  activeTeam: TeamResponse | null
  isAuthenticated: boolean

  setJwt: (jwt: string) => void
  setTgUser: (user: TgUser) => void
  setActiveTeam: (team: TeamResponse | null) => void
  logout: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      jwt: null,
      tgUser: null,
      activeTeam: null,
      isAuthenticated: false,

      setJwt: (jwt) => {
        localStorage.setItem('jwt', jwt)
        set({ jwt, isAuthenticated: true })
      },
      setTgUser: (tgUser) => set({ tgUser }),
      setActiveTeam: (activeTeam) => set({ activeTeam }),
      logout: () => {
        localStorage.removeItem('jwt')
        set({ jwt: null, isAuthenticated: false, activeTeam: null })
      },
    }),
    {
      name: 'teampilot-app',
      partialize: (state) => ({
        jwt: state.jwt,
        activeTeam: state.activeTeam,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
