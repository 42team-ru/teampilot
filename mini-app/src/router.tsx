import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAppStore } from '@/stores/appStore'
import { AppLayout } from '@/components/layout/AppLayout'
import { DashboardPage } from '@/pages/DashboardPage'
import { BoardPage } from '@/pages/BoardPage'
import { SyncPage } from '@/pages/SyncPage'
import { TeamsPage } from '@/pages/TeamsPage'
import { ProfilePage } from '@/pages/ProfilePage'
import { OnboardingPage } from '@/pages/OnboardingPage'
import { YouGileSetupPage } from '@/pages/YouGileSetupPage'

function ProtectedLayout() {
  const isAuthenticated = useAppStore((s) => s.isAuthenticated)
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
          <Route path="/sync" element={<SyncPage />} />
          <Route path="/teams" element={<TeamsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
