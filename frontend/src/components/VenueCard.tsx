import { useNavigate } from 'react-router-dom'
import type { SavedVenueStatus, Venue } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface VenueCardProps {
  venue: Venue
  isSaved: boolean
  onSave: () => void
  onRemove: () => void
  status?: SavedVenueStatus
  onStatusChange?: (status: SavedVenueStatus) => void
}

const STATUS_LABELS: Record<SavedVenueStatus, string> = {
  not_contacted: 'Not contacted',
  contacted: 'Contacted',
  replied: 'Replied',
  booked: 'Booked',
  declined: 'Declined',
}

export default function VenueCard({
  venue,
  isSaved,
  onSave,
  onRemove,
  status,
  onStatusChange,
}: VenueCardProps) {
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
    <div className="relative bg-cream border border-line rounded-xl p-4 flex flex-col gap-2">
      <h3 className="font-display font-bold text-lg text-ink">{venue.name}</h3>
      <p className="text-sm text-muted">{venue.address}</p>

      {hasContactInfo ? (
        <ul className="text-sm space-y-1.5 mt-1">
          {contact?.email && (
            <li className="flex items-center gap-2 text-ink">
              <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
              <a className="hover:text-teal-dark underline" href={`mailto:${contact.email}`}>
                {contact.email}
              </a>
            </li>
          )}
          {contact?.phone && (
            <li className="flex items-center gap-2 text-ink">
              <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
              {contact.phone}
            </li>
          )}
          {contact?.booking_url && (
            <li className="flex items-center gap-2 text-ink">
              <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
              <a
                className="underline hover:text-teal-dark"
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
              <li key={platform} className="flex items-center gap-2 text-ink">
                <span className="w-1.5 h-1.5 rounded-full bg-teal shrink-0" />
                <a className="underline hover:text-teal-dark capitalize" href={url} target="_blank" rel="noreferrer">
                  {platform}
                </a>
              </li>
            ))}
        </ul>
      ) : (
        <p className="text-sm text-muted/80 italic mt-1">No contact info found</p>
      )}

      {status !== undefined && onStatusChange ? (
        <div className="flex items-center justify-between mt-2 pt-3 border-t border-dashed border-line">
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value as SavedVenueStatus)}
            className="bg-cream border border-teal text-teal-dark rounded-lg px-2.5 py-1.5 font-display font-semibold text-xs uppercase tracking-wide"
          >
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={onRemove}
            className="font-display font-semibold text-xs uppercase tracking-wide text-[#c26b5a] hover:text-[#a5533f]"
          >
            Remove
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleToggleSave}
          className={
            isSaved
              ? 'absolute right-3 bottom-3 rounded-full border border-teal text-teal-dark px-3.5 py-1.5 font-display font-semibold text-xs uppercase tracking-wide'
              : 'absolute right-3 bottom-3 rounded-full bg-teal text-white px-3.5 py-1.5 font-display font-semibold text-xs uppercase tracking-wide'
          }
        >
          {isSaved ? 'Saved' : 'Save'}
        </button>
      )}
    </div>
  )
}
