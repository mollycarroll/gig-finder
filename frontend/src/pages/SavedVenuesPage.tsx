import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as api from '../api/client'
import type { SavedVenue } from '../api/client'
import VenueCard from '../components/VenueCard'
import { useAuth } from '../context/AuthContext'

export default function SavedVenuesPage() {
  const { user, loading: authLoading } = useAuth()
  const navigate = useNavigate()
  const [saved, setSaved] = useState<SavedVenue[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (authLoading) return
    if (!user) {
      navigate('/login')
      return
    }
    api
      .getSavedVenues()
      .then(setSaved)
      .catch(() => setError('Failed to load saved venues.'))
  }, [authLoading, user, navigate])

  async function handleRemove(venueId: number) {
    await api.unsaveVenue(venueId)
    setSaved((prev) => prev?.filter((s) => s.venue_id !== venueId) ?? null)
  }

  async function handleStatusChange(venueId: number, status: api.SavedVenueStatus) {
    try {
      const updated = await api.updateSavedVenueStatus(venueId, status)
      setSaved((prev) => prev?.map((s) => (s.venue_id === venueId ? updated : s)) ?? null)
    } catch {
      setError('Failed to update status.')
    }
  }

  if (authLoading || (saved === null && !error)) {
    return <p className="p-4 text-sm text-muted">Loading...</p>
  }

  return (
    <div className="p-4 max-w-2xl mx-auto flex flex-col gap-4">
      <h1 className="font-display font-bold text-2xl uppercase text-ink">
        Saved {saved && saved.length > 0 ? `(${saved.length})` : ''}
      </h1>
      {error && <p className="text-sm text-[#c26b5a]">{error}</p>}
      {saved?.length === 0 && <p className="text-sm text-muted">No saved venues yet.</p>}
      {saved?.map((s) => (
        <VenueCard
          key={s.venue_id}
          venue={s.venue}
          isSaved
          onSave={() => {}}
          onRemove={() => handleRemove(s.venue_id)}
          status={s.status}
          onStatusChange={(status) => handleStatusChange(s.venue_id, status)}
        />
      ))}
    </div>
  )
}
