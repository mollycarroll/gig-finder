import { supabase } from '../lib/supabaseClient'

// In dev this is empty and Vite's proxy (vite.config.ts) forwards /api to
// the local backend. In prod (GitHub Pages) there's no proxy, so requests
// must go directly to the deployed backend's absolute URL.
const API_BASE_URL = import.meta.env.VITE_API_URL ?? ''

export interface GeocodeResult {
  place_id: number
  display_name: string
  lat: number
  lon: number
}

export type ScrapeStatus = 'success' | 'no_website' | 'timeout' | 'disallowed_by_robots' | 'error'

export type SavedVenueStatus = 'not_contacted' | 'contacted' | 'replied' | 'booked' | 'declined'

export interface VenueContact {
  email: string | null
  phone: string | null
  social_links: Record<string, string>
  booking_url: string | null
  scrape_status: ScrapeStatus
}

export interface Venue {
  id: number
  name: string
  address: string
  lat: number
  lon: number
  website_url: string | null
  osm_phone: string | null
  contact: VenueContact | null
}

export interface SearchResponse {
  area_id: number
  display_name: string
  venues: Venue[]
}

export interface SavedVenue {
  id: number
  venue_id: number
  status: SavedVenueStatus
  created_at: string
  venue: Venue
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token

  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? response.statusText)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

// Queried straight from the browser rather than through the backend:
// Nominatim rate-limits shared-hosting IPs (like the deployed backend's),
// while each visitor's own IP stays well inside its usage policy.
const NOMINATIM_URL = 'https://nominatim.openstreetmap.org'

export async function geocode(query: string): Promise<GeocodeResult[]> {
  const response = await fetch(
    `${NOMINATIM_URL}/search?q=${encodeURIComponent(query)}&format=jsonv2`,
    { headers: { Accept: 'application/json' } },
  )
  if (!response.ok) {
    throw new ApiError(response.status, response.statusText)
  }
  const items: { place_id: number; display_name: string; lat: string; lon: string }[] =
    await response.json()
  return items.map((item) => ({
    place_id: item.place_id,
    display_name: item.display_name,
    lat: parseFloat(item.lat),
    lon: parseFloat(item.lon),
  }))
}

export function search(body: {
  lat: number
  lon: number
  display_name: string
  query_text?: string
  radius_m?: number
}): Promise<SearchResponse> {
  return apiFetch('/api/search', { method: 'POST', body: JSON.stringify(body) })
}

export function getSavedVenues(): Promise<SavedVenue[]> {
  return apiFetch('/api/saved-venues')
}

export function saveVenue(venueId: number): Promise<SavedVenue> {
  return apiFetch('/api/saved-venues', {
    method: 'POST',
    body: JSON.stringify({ venue_id: venueId }),
  })
}

export function unsaveVenue(venueId: number): Promise<void> {
  return apiFetch(`/api/saved-venues/${venueId}`, { method: 'DELETE' })
}

export function updateSavedVenueStatus(
  venueId: number,
  status: SavedVenueStatus,
): Promise<SavedVenue> {
  return apiFetch(`/api/saved-venues/${venueId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}
