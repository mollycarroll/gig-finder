import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SearchPage from '../pages/SearchPage'
import * as api from '../api/client'
import * as AuthContext from '../context/AuthContext'

vi.mock('../api/client', () => ({
  geocode: vi.fn(),
  search: vi.fn(),
  getSavedVenues: vi.fn(),
  saveVenue: vi.fn(),
  unsaveVenue: vi.fn(),
}))
vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <SearchPage />
    </MemoryRouter>,
  )
}

function search(query: string) {
  fireEvent.change(screen.getByPlaceholderText(/city, neighborhood/i), {
    target: { value: query },
  })
  fireEvent.click(screen.getByRole('button', { name: /search/i }))
}

describe('SearchPage', () => {
  beforeEach(() => {
    vi.mocked(AuthContext.useAuth).mockReturnValue({
      user: null,
      session: null,
      loading: false,
      signOut: vi.fn(),
    })
  })

  it('shows the disambiguation picker when geocode returns multiple candidates', async () => {
    vi.mocked(api.geocode).mockResolvedValue([
      { place_id: 1, display_name: 'Springfield, IL, USA', lat: 39.78, lon: -89.65 },
      { place_id: 2, display_name: 'Springfield, MA, USA', lat: 42.1, lon: -72.59 },
    ])

    renderPage()
    search('Springfield')

    await waitFor(() => {
      expect(screen.getByText('Springfield, IL, USA')).toBeInTheDocument()
      expect(screen.getByText('Springfield, MA, USA')).toBeInTheDocument()
    })
    expect(api.search).not.toHaveBeenCalled()
  })

  it('searches directly and renders results when geocode returns a single match', async () => {
    vi.mocked(api.geocode).mockResolvedValue([
      { place_id: 1, display_name: 'Asheville, NC, USA', lat: 35.6, lon: -82.55 },
    ])
    vi.mocked(api.search).mockResolvedValue({
      area_id: 1,
      display_name: 'Asheville, NC, USA',
      venues: [
        {
          id: 1,
          name: 'The Blue Note',
          address: '1 Main St',
          lat: 35.6,
          lon: -82.55,
          website_url: null,
          osm_phone: null,
          contact: null,
        },
      ],
    })

    renderPage()
    search('Asheville')

    await waitFor(() => {
      expect(screen.getByText('The Blue Note')).toBeInTheDocument()
    })
    expect(api.search).toHaveBeenCalledWith(
      expect.objectContaining({ display_name: 'Asheville, NC, USA', lat: 35.6, lon: -82.55 }),
    )
    expect(screen.queryByText(/multiple places match/i)).not.toBeInTheDocument()
  })

  it('runs the search after picking a disambiguation candidate', async () => {
    vi.mocked(api.geocode).mockResolvedValue([
      { place_id: 1, display_name: 'Springfield, IL, USA', lat: 39.78, lon: -89.65 },
      { place_id: 2, display_name: 'Springfield, MA, USA', lat: 42.1, lon: -72.59 },
    ])
    vi.mocked(api.search).mockResolvedValue({
      area_id: 1,
      display_name: 'Springfield, IL, USA',
      venues: [],
    })

    renderPage()
    search('Springfield')

    await waitFor(() => screen.getByText('Springfield, IL, USA'))
    fireEvent.click(screen.getByText('Springfield, IL, USA'))

    await waitFor(() => {
      expect(api.search).toHaveBeenCalledWith(
        expect.objectContaining({ lat: 39.78, lon: -89.65, display_name: 'Springfield, IL, USA' }),
      )
    })
    expect(screen.queryByText(/multiple places match/i)).not.toBeInTheDocument()
  })

  it('shows an error message when no places match', async () => {
    vi.mocked(api.geocode).mockResolvedValue([])

    renderPage()
    search('asdkjfhalksjdhf')

    await waitFor(() => {
      expect(screen.getByText(/no places found/i)).toBeInTheDocument()
    })
  })
})
