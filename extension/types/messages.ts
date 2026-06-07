import type { RecordingState } from './recording'

export type ExtMessage =
  | { type: 'START_RECORDING'; tabId: number; tabUrl?: string; tabTitle?: string; micDeviceId?: string }
  | { type: 'STOP_RECORDING' }
  | { type: 'PAUSE_RECORDING' }
  | { type: 'RESUME_RECORDING' }
  | { type: 'TOGGLE_MIC' }
  | { type: 'RESET_RECORDING' }
  | { type: 'ENSURE_OFFSCREEN' }
  | {
      type: 'AUDIO_CHUNK'
      chunk: number[]
      meetingId: string
      contentType: string
      finalChunk: boolean
    }
  | { type: 'OFFSCREEN_START'; streamId: string; meetingId: string; micDeviceId?: string }
  | { type: 'OFFSCREEN_PAUSE' }
  | { type: 'OFFSCREEN_RESUME' }
  | { type: 'OFFSCREEN_STOP' }
  | { type: 'OFFSCREEN_TOGGLE_MIC' }
  | { type: 'OFFSCREEN_TEST_AUDIO' }
  | { type: 'AUDIO_LEVEL'; level: number }
  | { type: 'REQUEST_TEST_AUDIO' }
  | { type: 'RECORDING_STARTED'; meetingId: string }
  | { type: 'RECORDING_ERROR'; error: string }
  | { type: 'PROCESSING_DONE'; meetingId: string }
  | { type: 'STATE_UPDATE'; state: RecordingState }
