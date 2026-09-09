import type { GeocodeResult } from '../api/client'

interface AreaDisambiguationPickerProps {
  candidates: GeocodeResult[]
  onSelect: (candidate: GeocodeResult) => void
}

export default function AreaDisambiguationPicker({
  candidates,
  onSelect,
}: AreaDisambiguationPickerProps) {
  return (
    <div className="bg-cream border border-line rounded-xl p-4">
      <p className="mb-2 text-sm text-muted">Multiple places match — which one did you mean?</p>
      <ul className="flex flex-col gap-1">
        {candidates.map((candidate) => (
          <li key={candidate.place_id}>
            <button
              type="button"
              onClick={() => onSelect(candidate)}
              className="text-left text-sm text-ink underline hover:text-teal-dark"
            >
              {candidate.display_name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
