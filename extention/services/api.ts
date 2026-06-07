import { getAuthSession } from './auth'
import { getApiBaseUrl } from './config'
import { getMeetingResultsState } from './storage'
import type { MeetingResponse, MeetingResults } from '../types/recording'

export async function getMeetingByUrl(meetingUrl: string): Promise<MeetingResponse> {
  const params = new URLSearchParams({ meetingUrl })
  return requestJson<MeetingResponse>(`/meetings/by-url?${params.toString()}`)
}

export async function createMeeting(teamId: string, meetingUrl: string): Promise<MeetingResponse> {
  return requestJson<MeetingResponse>('/meetings', {
    method: 'POST',
    body: JSON.stringify({ teamId, meetingUrl }),
  })
}

export async function getMeetingResults(meetingId: string): Promise<MeetingResults> {
  const results = await getMeetingResultsState()
  if (results?.meetingId === meetingId) return results
  throw new Error('Результаты встречи ещё не получены')
}

export async function createTask(_meetingId: string, _taskId: string): Promise<void> {
  throw new Error('Создание задач из live meeting пока выполняется backend-side')
}

async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = await getAuthSession()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (session?.token) {
    headers.set('Authorization', `Bearer ${session.token}`)
  }

  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers,
  })

  if (!response.ok) {
    throw new Error(await readBackendError(response))
  }

  return response.json() as Promise<T>
}

async function readBackendError(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    if (typeof data?.message === 'string') return data.message
    if (typeof data?.title === 'string') return data.title
  } catch {
    // ignore invalid JSON and use status text
  }
  return response.statusText || `HTTP ${response.status}`
}
