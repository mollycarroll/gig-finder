import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SavedVenuesPage from '../pages/SavedVenuesPage'
import * as api from '../api/client'
import * as AuthContext from '../context/AuthContext'
import type { SavedVenue } from '../api/client'

vi.mock('../api/client', () => ({
  getSavedVenues: vi.fn(),
  unsaveVenue: vi.fn(),
  updateSavedVenueStatus: vi.fn(),
}))
vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const baseSaved: SavedVenue = {
  id: 1,
  venue_id: 1,
  status: 'not_contacted',
  created_at: '2026-09-01T00:00:00Z',
  venue: {
    id: 1,
    name: 'The Blue Note',
    address: '1 Main St',
    lat: 35.6,
    lon: -82.55,
    website_url: null,
    osm_phone: null,
    contact: null,
  },
}

function mockUser(user: { id: string } | null) {
  vi.mocked(AuthContext.useAuth).mockReturnValue({
    user: user as never,
    session: null,
    loading: false,
    signOut: vi.fn(),
  })
}

function renderPage() {
  return render(
    <MemoryRouter>
      <SavedVenuesPage />
    </MemoryRouter>,
  )
}

describe('SavedVenuesPage', () => {
  beforeEach(() => {
    mockUser({ id: 'user-1' })
  })

  it('renders saved venues with their current status', async () => {
    vi.mocked(api.getSavedVenues).mockResolvedValue([baseSaved])

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('The Blue Note')).toBeInTheDocument()
    })
    expect(screen.getByRole('combobox')).toHaveValue('not_contacted')
  })

  it('updates status and re-renders with the server response on select change', async () => {
    vi.mocked(api.getSavedVenues).mockResolvedValue([baseSaved])
    vi.mocked(api.updateSavedVenueStatus).mockResolvedValue({
      ...baseSaved,
      status: 'contacted',
    })

    renderPage()
    await waitFor(() => screen.getByRole('combobox'))

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'contacted' } })

    await waitFor(() => {
      expect(screen.getByRole('combobox')).toHaveValue('contacted')
    })
    expect(api.updateSavedVenueStatus).toHaveBeenCalledWith(1, 'contacted')
  })

  it('shows an error message when the status update fails', async () => {
    vi.mocked(api.getSavedVenues).mockResolvedValue([baseSaved])
    vi.mocked(api.updateSavedVenueStatus).mockRejectedValue(new Error('failed'))

    renderPage()
    await waitFor(() => screen.getByRole('combobox'))

    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'booked' } })

    await waitFor(() => {
      expect(screen.getByText(/failed to update status/i)).toBeInTheDocument()
    })
  })
})
