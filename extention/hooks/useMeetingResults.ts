import { useState, useEffect } from 'react'
import { type MeetingResults } from '../types/recording'
import { getMeetingResults } from '../services/api'

export function useMeetingResults(meetingId: string | undefined) {
  const [results, setResults] = useState<MeetingResults | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!meetingId) return
    setLoading(true)
    setError(null)
    getMeetingResults(meetingId)
      .then(setResults)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false))
  }, [meetingId])

  return { results, loading, error }
}
