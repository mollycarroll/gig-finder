import { useState, type FormEvent } from 'react'
import * as api from '../api/client'
import type { GeocodeResult, Venue } from '../api/client'
import AreaDisambiguationPicker from '../components/AreaDisambiguationPicker'
import VenueCard from '../components/VenueCard'
import { useAuth } from '../context/AuthContext'

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [candidates, setCandidates] = useState<GeocodeResult[] | null>(null)
  const [venues, setVenues] = useState<Venue[] | null>(null)
  const [savedVenueIds, setSavedVenueIds] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return

    setError(null)
    setCandidates(null)
    setVenues(null)
    setLoading(true)
    try {
      const results = await api.geocode(query)
      if (results.length === 0) {
        setError('No places found for that search.')
      } else if (results.length === 1) {
        await runSearch(results[0])
      } else {
        setCandidates(results)
      }
    } catch {
      setError('Something went wrong looking up that place.')
    } finally {
      setLoading(false)
    }
  }

  async function runSearch(candidate: GeocodeResult) {
    setLoading(true)
    setError(null)
    setCandidates(null)
    try {
      const response = await api.search({
        lat: candidate.lat,
        lon: candidate.lon,
        display_name: candidate.display_name,
        query_text: query,
      })
      setVenues(response.venues)

      if (user) {
        const saved = await api.getSavedVenues()
        setSavedVenueIds(new Set(saved.map((s) => s.venue_id)))
      }
    } catch {
      setError('Search failed — try a smaller area.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(venueId: number) {
    await api.saveVenue(venueId)
    setSavedVenueIds((prev) => new Set(prev).add(venueId))
  }

  async function handleRemove(venueId: number) {
    await api.unsaveVenue(venueId)
    setSavedVenueIds((prev) => {
      const next = new Set(prev)
      next.delete(venueId)
      return next
    })
  }

  return (
    <div className="p-4 max-w-2xl mx-auto flex flex-col gap-4">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className="flex-1 bg-cream border border-line rounded-lg px-3 py-2.5 text-sm placeholder:text-muted focus:outline-none focus:border-teal"
          placeholder="City, neighborhood, venue area..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          type="submit"
          className="px-4 py-2.5 rounded-lg bg-ink text-white font-display font-semibold text-sm uppercase tracking-wide disabled:opacity-50"
          disabled={loading}
        >
          {loading ? 'Searching...' : 'Go'}
        </button>
      </form>

      {error && <p className="text-sm text-[#c26b5a]">{error}</p>}

      {candidates && <AreaDisambiguationPicker candidates={candidates} onSelect={runSearch} />}

      {venues && (
        <div className="flex flex-col gap-3.5">
          {venues.length === 0 && (
            <p className="text-sm text-muted">No venues found in this area.</p>
          )}
          {venues.map((venue, i) => (
            <div key={venue.id}>
              {i > 0 && <div className="ticket-divider mb-3.5" />}
              <VenueCard
                venue={venue}
                isSaved={savedVenueIds.has(venue.id)}
                onSave={() => handleSave(venue.id)}
                onRemove={() => handleRemove(venue.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
