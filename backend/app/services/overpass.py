import asyncio
from dataclasses import dataclass

import httpx

from app.config import settings

# Large-radius queries routinely need more than 25s on the public mirrors.
_TIMEOUT = httpx.Timeout(60.0)
# Public Overpass mirrors answer 429 when rate limiting and 502/503/504 when
# overloaded; both are worth a short backoff-and-retry.
_RETRYABLE_STATUSES = {429, 502, 503, 504}
_USER_AGENT = "gig-finder/1.0 (local dev; https://github.com/)"
_MAX_RETRIES = 3

# OSM tags considered live-music-relevant. Adjustable without a migration —
# this only shapes the Overpass query, not stored data.
_LIVE_MUSIC_AMENITIES = ["bar", "pub", "nightclub", "music_venue"]


@dataclass
class OverpassVenue:
    osm_id: int
    osm_type: str  # "node" | "way" | "relation"
    name: str
    address: str
    lat: float
    lon: float
    website_url: str | None
    osm_phone: str | None
    osm_tags: dict


def _build_query(lat: float, lon: float, radius_m: int) -> str:
    amenity_filter = "|".join(_LIVE_MUSIC_AMENITIES)
    around = f"(around:{radius_m},{lat},{lon})"
    tag_filter = f'["amenity"~"^({amenity_filter})$"]'
    return (
        "[out:json][timeout:50];"
        "("
        f"node{tag_filter}{around};"
        f"way{tag_filter}{around};"
        f"relation{tag_filter}{around};"
        ");"
        "out center tags;"
    )


def _extract_address(tags: dict) -> str:
    street = " ".join(
        p for p in (tags.get("addr:housenumber"), tags.get("addr:street")) if p
    )
    return ", ".join(p for p in (street, tags.get("addr:city")) if p)


def _parse_element(element: dict) -> OverpassVenue:
    tags = element.get("tags", {})
    if element["type"] == "node":
        lat, lon = element["lat"], element["lon"]
    else:
        lat, lon = element["center"]["lat"], element["center"]["lon"]

    return OverpassVenue(
        osm_id=element["id"],
        osm_type=element["type"],
        name=tags.get("name", "Unnamed venue"),
        address=_extract_address(tags),
        lat=lat,
        lon=lon,
        website_url=tags.get("website") or tags.get("contact:website"),
        osm_phone=tags.get("phone") or tags.get("contact:phone"),
        osm_tags=tags,
    )


async def find_venues(
    lat: float, lon: float, radius_m: int, client: httpx.AsyncClient | None = None
) -> list[OverpassVenue]:
    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=_TIMEOUT)

    try:
        for attempt in range(_MAX_RETRIES):
            response = await client.post(
                settings.OVERPASS_API_URL,
                data={"data": _build_query(lat, lon, radius_m)},
                headers={"User-Agent": _USER_AGENT},
            )
            if response.status_code in _RETRYABLE_STATUSES and attempt < _MAX_RETRIES - 1:
                delay = float(response.headers.get("Retry-After", 1 << attempt))
                await asyncio.sleep(delay)
                continue
            response.raise_for_status()
            break
        data = response.json()
    finally:
        if owns_client:
            await client.aclose()

    return [_parse_element(el) for el in data.get("elements", [])]


def prioritize(venues: list[OverpassVenue], cap: int) -> list[OverpassVenue]:
    """Trim a large venue list to the entries most likely to yield contact info.

    Order: venues with a website first (scrapable for email/booking links),
    then ones with a phone number in OSM, then ones with at least an address.
    The sort is stable, so ties keep Overpass's original order. Used for
    large-radius searches so the scrape pass stays bounded.
    """

    def sort_key(v: OverpassVenue) -> tuple[bool, bool, bool]:
        return (v.website_url is None, v.osm_phone is None, not v.address)

    return sorted(venues, key=sort_key)[:cap]
