import { useState, useEffect } from 'react'
import { type MeetingResults } from '../types/recording'
import { getMeetingResultsState, watchMeetingResults } from '../services/storage'

export function useMeetingResults(meetingId: string | undefined) {
  const [results, setResults] = useState<MeetingResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!meetingId) {
      setResults(null)
      return
    }
    setLoading(true)
    setError(null)
    getMeetingResultsState()
      .then((stored) => {
        setResults(stored?.meetingId === meetingId ? stored : null)
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))

    return watchMeetingResults((stored) => {
      setResults(stored?.meetingId === meetingId ? stored : null)
    })
  }, [meetingId])

  return { results, loading, error }
}
