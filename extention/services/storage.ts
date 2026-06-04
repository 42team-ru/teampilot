import { type RecordingState, defaultRecordingState } from '../types/recording'

const KEY = 'recordingState'

export async function getRecordingState(): Promise<RecordingState> {
  const result = await chrome.storage.session.get(KEY)
  return (result[KEY] as RecordingState) ?? defaultRecordingState()
}

export async function setRecordingState(state: RecordingState): Promise<void> {
  await chrome.storage.session.set({ [KEY]: state })
}

export function watchRecordingState(cb: (state: RecordingState) => void): () => void {
  const handler = (changes: Record<string, chrome.storage.StorageChange>) => {
    if (KEY in changes) {
      cb(changes[KEY].newValue as RecordingState)
    }
  }
  chrome.storage.session.onChanged.addListener(handler)
  return () => chrome.storage.session.onChanged.removeListener(handler)
}
