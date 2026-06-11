import { useEffect } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import { teamsApi } from '@/api/teams'
import { AppLayout } from '@/components/layout/AppLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { BoardPage } from '@/pages/BoardPage'
import { WorkloadPage } from '@/pages/WorkloadPage'
import { SyncPage } from '@/pages/SyncPage'
import { TeamsPage } from '@/pages/TeamsPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { YouGileSetupPage } from '@/pages/YouGileSetupPage'

function ProtectedLayout() {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated)
  const activeTeam = useAppStore((s) => s.activeTeam)
  const setActiveTeam = useAppStore((s) => s.setActiveTeam)

  useEffect(() => {
    if (isAuthenticated && !activeTeam) {
      teamsApi.listMemberOf().then((teams) => {
        if (teams.length > 0) setActiveTeam(teams[0])
      }).catch(() => {})
    }
  }, [isAuthenticated, activeTeam, setActiveTeam])

  if (!isAuthenticated) return <Navigate to="/onboarding" replace />
  return <AppLayout />
}

export function Router() {
  return (
    <BrowserRouter basename="/app">
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/onboarding/yougile" element={<YouGileSetupPage />} />
        <Route element={<ProtectedLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="/board" element={<BoardPage />} />
          <Route path="/workload" element={<WorkloadPage />} />
          <Route path="/sync" element={<SyncPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
