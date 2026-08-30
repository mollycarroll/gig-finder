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
    <div className="border border-gray-200 rounded-lg p-4">
      <p className="mb-2 text-sm text-gray-600">
        Multiple places match — which one did you mean?
      </p>
      <ul className="space-y-1">
        {candidates.map((candidate) => (
          <li key={candidate.place_id}>
            <button
              type="button"
              onClick={() => onSelect(candidate)}
              className="underline text-left hover:text-purple-700"
            >
              {candidate.display_name}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
