export type RecordingStatus =
  | 'idle'
  | 'starting'
  | 'recording'
  | 'paused'
  | 'processing'
  | 'error'
  | 'done'

export interface RecordingState {
  status: RecordingStatus
  meetingId?: string
  teamId?: string
  primaryRecorderTelegramId?: number
  startedAt?: number
  pausedAt?: number
  totalPausedMs: number
  chunks: number
  bytes: number
  error?: string
  micEnabled: boolean
  micMuted: boolean
  micDeviceId?: string
  tabId?: number
  tabUrl?: string
  tabTitle?: string
  startingStep?: 0 | 1 | 2
}

export function defaultRecordingState(): RecordingState {
  return {
    status: 'idle',
    chunks: 0,
    bytes: 0,
    totalPausedMs: 0,
    micEnabled: true,
    micMuted: false,
  }
}

export interface Task {
  id: string
  title: string
  description?: string
  assignee?: string
  deadline?: string
  confidence: number
  source: string
  status: 'pending' | 'created' | 'rejected' | 'incomplete' | 'detected'
}

export interface Decision {
  id: string
  text: string
  timestamp: string
}

export interface LiveEvent {
  id: string
  time: string
  text: string
  type: 'event' | 'alert'
}

export interface Summary {
  goal: string
  topics: string[]
  decisions: string[]
  risks: string[]
  nextSteps: string[]
}

export interface MeetingResults {
  meetingId: string
  duration: number
  tasks: Task[]
  decisions: Decision[]
  liveEvents: LiveEvent[]
  summary: Summary
}

export interface AuthSession {
  userId: string
  telegramId: number
  systemRole: string
  token: string
}

export interface ExtensionLoginChallenge {
  code: string
  expiresAt: string
  botUsername: string
}

export interface ExtensionLoginStartResponse {
  code: string
  expiresAt: string
}

export interface ExtensionLoginStatusResponse {
  status: 'pending' | 'confirmed' | 'expired'
  code: string
  expiresAt: string
  auth?: AuthSession
}

export interface MeetingResponse {
  id: string
  teamId: string
  meetingUrl: string
  primaryRecorderTelegramId?: number
  active: boolean
  createdAt: string
}

export interface MeetingLiveResult {
  meetingId: string
  teamId: string
  chunkIndex?: number
  transcript?: string
  summary?: string
  context?: string
  tasks?: MeetingLiveTask[]
  statuses?: MeetingLiveStatus[]
}

export interface MeetingLiveTask {
  title: string
  description?: string
  assigneeId?: number
  deadline?: string
  columnId?: string
  confidence: number
}

export interface MeetingLiveStatus {
  taskId?: string
  assigneeId?: number
  columnId?: string
  action?: string
}

export interface MeetingAudioChunkPayload {
  chunkIndex: number
  audioBase64: string
  contentType: string
  originalFilename: string
  finalChunk: boolean
}
