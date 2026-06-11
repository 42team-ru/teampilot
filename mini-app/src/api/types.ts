export type SystemRole = 'USER' | 'BOT' | 'SYSTEM_ADMIN'
export type TeamRole = 'MANAGER' | 'PARTICIPANT'
export type TaskLocalStatus = 'PENDING_APPROVAL' | 'ACTIVE' | 'DELETED_FROM_YOUGILE'
export type TaskSyncStatus = 'PENDING_SYNC' | 'SYNCED' | 'SYNC_FAILED'

export interface AuthResponse {
  userId: string
  telegramId: number
  systemRole: SystemRole
  token: string
}

export interface UserResponse {
  id: string
  telegramId: number
  telegramLogin?: string
  firstName?: string
  lastName?: string
}

export interface TeamResponse {
  id: string
  telegramChatId?: number
  chatTitle?: string
  kanbanId?: string
  active: boolean
}

export interface TeamMemberResponse {
  id: string
  telegramId: number
  telegramLogin?: string
  firstName?: string
  lastName?: string
  role: TeamRole
}

export interface TaskColumnResponse {
  id: string
  youGileColumnId?: string
  title: string
}

export interface AssigneeInfo {
  teamUserId: string
  telegramId: number
  telegramLogin?: string
  firstName?: string
  lastName?: string
}

export interface ColumnInfo {
  columnId: string
  youGileColumnId?: string
  title: string
}

export interface TaskResponse {
  id: string
  teamId: string
  title: string
  description?: string
  deadline?: string
  localStatus: TaskLocalStatus
  syncStatus: TaskSyncStatus
  externalId?: string
  column?: ColumnInfo
  assignee?: AssigneeInfo
  author?: AssigneeInfo
  createdAt: string
  completed: boolean
}

export interface PageResponse<T> {
  content: T[]
  totalElements: number
  totalPages: number
  number: number
  size: number
}

export interface SyncActiveTask {
  id: string
  title: string
  description?: string
  deadline?: string
  assignee?: AssigneeInfo
}

export interface ReminderSettingsResponse {
  maxRemindersPerTaskPerDay?: number
  quietHoursStart?: number
  quietHoursEnd?: number
  deadlineReminderMinutesBefore?: number
}

export interface YouGileCompanyResponse {
  companies?: Array<{ id: string; name: string }>
  token?: string
}

export interface YouGileBoardResponse {
  boards: Array<{ id: string; name: string }>
}

export interface PendingTeamChatResponse {
  id: string
  telegramChatId: number
  chatTitle?: string
}

export interface UploadedFileResponse {
  id: string
  filename: string
  presignedUrl: string
  createdAt: string
}

export interface TeamPaymentInitiateResponse {
  paymentUrl: string
  sessionId: string
}
