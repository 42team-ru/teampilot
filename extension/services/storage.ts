import {
  type LiveEvent,
  type MeetingLiveResult,
  type MeetingResults,
  type RecordingState,
  type Summary,
  type Task,
  defaultRecordingState,
} from '../types/recording'

const RECORDING_KEY = 'recordingState'
const RESULTS_KEY = 'meetingResults'

export async function getRecordingState(): Promise<RecordingState> {
  const result = await chrome.storage.local.get(RECORDING_KEY)
  return (result[RECORDING_KEY] as RecordingState) ?? defaultRecordingState()
}

export async function setRecordingState(state: RecordingState): Promise<void> {
  await chrome.storage.local.set({ [RECORDING_KEY]: state })
}

export function watchRecordingState(cb: (state: RecordingState) => void): () => void {
  const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
    if (RECORDING_KEY in changes) {
      cb(changes[RECORDING_KEY].newValue as RecordingState)
    }
  }
  chrome.storage.local.onChanged.addListener(handler)
  return () => chrome.storage.local.onChanged.removeListener(handler)
}

export async function getMeetingResultsState(): Promise<MeetingResults | null> {
  const result = await chrome.storage.local.get(RESULTS_KEY)
  return (result[RESULTS_KEY] as MeetingResults | undefined) ?? null
}

export async function setMeetingResultsState(results: MeetingResults): Promise<void> {
  await chrome.storage.local.set({ [RESULTS_KEY]: results })
}

export async function resetMeetingResults(meetingId: string): Promise<void> {
  await setMeetingResultsState(defaultMeetingResults(meetingId))
}

export function watchMeetingResults(cb: (results: MeetingResults | null) => void): () => void {
  const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
    if (RESULTS_KEY in changes) {
      cb((changes[RESULTS_KEY].newValue as MeetingResults | undefined) ?? null)
    }
  }
  chrome.storage.local.onChanged.addListener(handler)
  return () => chrome.storage.local.onChanged.removeListener(handler)
}

export async function applyMeetingLiveResult(event: MeetingLiveResult): Promise<MeetingResults> {
  const current = await getMeetingResultsState()
  const base =
    current?.meetingId === event.meetingId ? current : defaultMeetingResults(event.meetingId)

  const liveEvents = [...base.liveEvents]
  if (event.transcript?.trim()) {
    liveEvents.push(toTranscriptLiveEvent(event))
  }
  for (const status of event.statuses ?? []) {
    liveEvents.push(toStatusLiveEvent(event, status.action ?? 'STATUS'))
  }

  const tasks = mergeTasks(base.tasks, event)
  const summary = event.summary?.trim() ? toSummary(event.summary) : base.summary

  const next: MeetingResults = {
    ...base,
    tasks,
    liveEvents,
    summary,
  }
  await setMeetingResultsState(next)
  return next
}

function defaultMeetingResults(meetingId: string): MeetingResults {
  return {
    meetingId,
    duration: 0,
    tasks: [],
    decisions: [],
    liveEvents: [],
    summary: {
      goal: '',
      topics: [],
      decisions: [],
      risks: [],
      nextSteps: [],
    },
  }
}

function toTranscriptLiveEvent(event: MeetingLiveResult): LiveEvent {
  return {
    id: `transcript-${event.chunkIndex ?? Date.now()}-${Date.now()}`,
    time: formatClock(),
    text: event.transcript ?? '',
    type: 'event',
  }
}

function toStatusLiveEvent(event: MeetingLiveResult, action: string): LiveEvent {
  const chunk = event.chunkIndex !== undefined ? `chunk ${event.chunkIndex}` : 'live'
  return {
    id: `status-${chunk}-${action}-${Date.now()}`,
    time: formatClock(),
    text: `Обновление статуса задачи: ${action}`,
    type: 'alert',
  }
}

function toSummary(text: string): Summary {
  return {
    goal: text,
    topics: [],
    decisions: [],
    risks: [],
    nextSteps: [],
  }
}

function mergeTasks(existing: Task[], event: MeetingLiveResult): Task[] {
  const next = [...existing]
  for (const [index, task] of (event.tasks ?? []).entries()) {
    const id = taskId(event, index, task.title)
    const mapped: Task = {
      id,
      title: task.title,
      description: task.description,
      assignee: task.assigneeId ? String(task.assigneeId) : undefined,
      deadline: task.deadline,
      confidence: task.confidence,
      source:
        event.chunkIndex !== undefined
          ? `Чанк ${event.chunkIndex}`
          : 'Live transcription',
      status: 'detected',
    }
    const currentIndex = next.findIndex((item) => item.id === id)
    if (currentIndex >= 0) {
      next[currentIndex] = { ...next[currentIndex], ...mapped }
    } else {
      next.push(mapped)
    }
  }
  return next
}

function taskId(event: MeetingLiveResult, index: number, title: string): string {
  const chunk = event.chunkIndex ?? 'live'
  return `${event.meetingId}-${chunk}-${index}-${title}`.replace(/\s+/g, '-')
}

function formatClock(): string {
  return new Date().toLocaleTimeString('ru-RU', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}
