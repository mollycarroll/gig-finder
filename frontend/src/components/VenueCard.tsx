import { useNavigate } from 'react-router-dom'
import type { Venue } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface VenueCardProps {
  venue: Venue
  isSaved: boolean
  onSave: () => void
  onRemove: () => void
}

export default function VenueCard({ venue, isSaved, onSave, onRemove }: VenueCardProps) {
  const { user } = useAuth()
  const navigate = useNavigate()
  const contact = venue.contact

  const hasContactInfo =
    !!contact &&
    (contact.email ||
      contact.phone ||
      contact.booking_url ||
      Object.keys(contact.social_links ?? {}).length > 0)

  function handleToggleSave() {
    if (!user) {
      navigate('/login')
      return
    }
    if (isSaved) {
      onRemove()
    } else {
      onSave()
    }
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4 flex flex-col gap-2">
      <h3 className="text-lg font-semibold">{venue.name}</h3>
      <p className="text-sm text-gray-600">{venue.address}</p>

      {hasContactInfo ? (
        <ul className="text-sm space-y-1">
          {contact?.email && (
            <li>
              Email:{' '}
              <a className="underline" href={`mailto:${contact.email}`}>
                {contact.email}
              </a>
            </li>
          )}
          {contact?.phone && <li>Phone: {contact.phone}</li>}
          {contact?.booking_url && (
            <li>
              <a
                className="underline"
                href={contact.booking_url}
                target="_blank"
                rel="noreferrer"
              >
                Booking page
              </a>
            </li>
          )}
          {contact &&
            Object.entries(contact.social_links ?? {}).map(([platform, url]) => (
              <li key={platform}>
                <a className="underline" href={url} target="_blank" rel="noreferrer">
                  {platform}
                </a>
              </li>
            ))}
        </ul>
      ) : (
        <p className="text-sm text-gray-400 italic">No contact info found</p>
      )}

      <button
        type="button"
        onClick={handleToggleSave}
        className="mt-2 self-start px-3 py-1 rounded bg-purple-600 text-white text-sm"
      >
        {isSaved ? 'Remove' : 'Save'}
      </button>
    </div>
  )
}
