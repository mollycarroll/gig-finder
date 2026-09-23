from dataclasses import dataclass

import httpx

from app.config import settings

_TIMEOUT = httpx.Timeout(10.0)
_USER_AGENT = "gig-finder/1.0 (local dev; https://github.com/)"


@dataclass
class GeocodeCandidate:
    place_id: int
    display_name: str
    lat: float
    lon: float


async def geocode(
    query: str, client: httpx.AsyncClient | None = None
) -> list[GeocodeCandidate]:
    """Look up candidate places for a free-text query via Nominatim.

    Returns one candidate per match; an ambiguous query (e.g. "Springfield")
    naturally returns multiple, which the frontend uses to show a
    disambiguation picker.
    """
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=_TIMEOUT)

    try:
        response = await client.get(
            f"{settings.NOMINATIM_URL}/search",
            params={"q": query, "format": "jsonv2"},
            headers={"User-Agent": _USER_AGENT},
        )
        response.raise_for_status()
        results = response.json()
    finally:
        if owns_client:
            await client.aclose()

    return [
        GeocodeCandidate(
            place_id=item["place_id"],
            display_name=item["display_name"],
            lat=float(item["lat"]),
            lon=float(item["lon"]),
        )
        for item in results
    ]
