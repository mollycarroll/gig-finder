import { supabase } from '../lib/supabaseClient'

export interface GeocodeResult {
  place_id: number
  display_name: string
  lat: number
  lon: number
}

export type ScrapeStatus = 'success' | 'no_website' | 'timeout' | 'disallowed_by_robots' | 'error'

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

  const response = await fetch(path, { ...init, headers })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.detail ?? response.statusText)
  }

  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export function geocode(query: string): Promise<GeocodeResult[]> {
  return apiFetch(`/api/geocode?q=${encodeURIComponent(query)}`)
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
