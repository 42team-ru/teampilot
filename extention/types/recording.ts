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
  assignee?: string
  deadline?: string
  confidence: number
  source: string
  status: 'pending' | 'created' | 'rejected' | 'incomplete'
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
