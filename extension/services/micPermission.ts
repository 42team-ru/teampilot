export interface PendingRecordingTarget {
  tabId: number
  tabUrl?: string
  tabTitle?: string
  micDeviceId?: string
}

const PENDING_TARGET_KEY = 'pendingRecordingTarget'

export async function setPendingRecordingTarget(
  target: PendingRecordingTarget,
): Promise<void> {
  await chrome.storage.session.set({ [PENDING_TARGET_KEY]: target })
}

export async function getPendingRecordingTarget(): Promise<PendingRecordingTarget | null> {
  const result = await chrome.storage.session.get(PENDING_TARGET_KEY)
  return (result[PENDING_TARGET_KEY] as PendingRecordingTarget | undefined) ?? null
}

export async function clearPendingRecordingTarget(): Promise<void> {
  await chrome.storage.session.remove(PENDING_TARGET_KEY)
}

export async function openMicrophonePermissionPage(): Promise<void> {
  await chrome.tabs.create({
    url: chrome.runtime.getURL('mic-permission.html'),
  })
}
