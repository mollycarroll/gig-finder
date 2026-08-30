import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import VenueCard from '../components/VenueCard'
import type { Venue } from '../api/client'
import * as AuthContext from '../context/AuthContext'

vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const baseVenue: Venue = {
  id: 1,
  name: 'The Blue Note',
  address: '1 Main St, Asheville',
  lat: 35.6,
  lon: -82.55,
  website_url: 'https://thebluenote.example',
  osm_phone: null,
  contact: null,
}

function mockUser(user: { id: string } | null) {
  vi.mocked(AuthContext.useAuth).mockReturnValue({
    user: user as never,
    session: null,
    loading: false,
    signOut: vi.fn(),
  })
}

function renderCard(props: Partial<React.ComponentProps<typeof VenueCard>> = {}) {
  return render(
    <MemoryRouter>
      <VenueCard
        venue={baseVenue}
        isSaved={false}
        onSave={vi.fn()}
        onRemove={vi.fn()}
        {...props}
      />
    </MemoryRouter>,
  )
}

describe('VenueCard', () => {
  beforeEach(() => {
    mockUser({ id: 'user-1' })
  })

  it('renders the venue name and address', () => {
    renderCard()
    expect(screen.getByText('The Blue Note')).toBeInTheDocument()
    expect(screen.getByText('1 Main St, Asheville')).toBeInTheDocument()
  })

  it('shows the missing-contact-info state when there is no contact', () => {
    renderCard()
    expect(screen.getByText(/no contact info found/i)).toBeInTheDocument()
  })

  it('renders email, phone, booking link, and social links when present', () => {
    renderCard({
      venue: {
        ...baseVenue,
        contact: {
          email: 'info@thebluenote.example',
          phone: '(555) 867-5309',
          social_links: { instagram: 'https://instagram.com/thebluenote' },
          booking_url: 'https://thebluenote.example/book',
          scrape_status: 'success',
        },
      },
    })

    expect(screen.getByText('info@thebluenote.example')).toBeInTheDocument()
    expect(screen.getByText((_, node) => node?.textContent === 'Phone: (555) 867-5309')).toBeInTheDocument()
    expect(screen.getByText('Booking page')).toBeInTheDocument()
    expect(screen.getByText('instagram')).toBeInTheDocument()
    expect(screen.queryByText(/no contact info found/i)).not.toBeInTheDocument()
  })

  it('calls onSave when Save is clicked and not yet saved', () => {
    const onSave = vi.fn()
    renderCard({ onSave })

    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('calls onRemove when Remove is clicked and already saved', () => {
    const onRemove = vi.fn()
    renderCard({ isSaved: true, onRemove })

    fireEvent.click(screen.getByRole('button', { name: /remove/i }))

    expect(onRemove).toHaveBeenCalledTimes(1)
  })

  it('does not save and redirects to login instead when logged out', () => {
    mockUser(null)
    const onSave = vi.fn()
    renderCard({ onSave })

    fireEvent.click(screen.getByRole('button', { name: /save/i }))

    expect(onSave).not.toHaveBeenCalled()
  })
})
