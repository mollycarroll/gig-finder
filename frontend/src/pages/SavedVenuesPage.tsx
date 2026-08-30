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

  if (authLoading || (saved === null && !error)) {
    return <p className="p-4">Loading...</p>
  }

  return (
    <div className="p-4 max-w-2xl mx-auto flex flex-col gap-4">
      <h1 className="text-2xl font-semibold">Saved venues</h1>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {saved?.length === 0 && <p className="text-sm text-gray-500">No saved venues yet.</p>}
      {saved?.map((s) => (
        <VenueCard
          key={s.venue_id}
          venue={s.venue}
          isSaved
          onSave={() => {}}
          onRemove={() => handleRemove(s.venue_id)}
        />
      ))}
    </div>
  )
}
