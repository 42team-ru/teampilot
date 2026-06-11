import { create } from 'zustand'

interface UiState {
  activeTab: 'dashboard' | 'board' | 'sync' | 'teams' | 'profile'
  taskDetailId: string | null
  createTaskOpen: boolean

  setActiveTab: (tab: UiState['activeTab']) => void
  openTaskDetail: (id: string) => void
  closeTaskDetail: () => void
  setCreateTaskOpen: (open: boolean) => void
}

export const useUiStore = create<UiState>((set) => ({
  activeTab: 'dashboard',
  taskDetailId: null,
  createTaskOpen: false,

  setActiveTab: (activeTab) => set({ activeTab }),
  openTaskDetail: (taskDetailId) => set({ taskDetailId }),
  closeTaskDetail: () => set({ taskDetailId: null }),
  setCreateTaskOpen: (createTaskOpen) => set({ createTaskOpen }),
}))
