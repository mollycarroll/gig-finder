from dataclasses import dataclass

import httpx

from app.config import settings

_TIMEOUT = httpx.Timeout(25.0)

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
        "[out:json][timeout:25];"
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
        response = await client.post(
            settings.OVERPASS_API_URL,
            data={"data": _build_query(lat, lon, radius_m)},
        )
        response.raise_for_status()
        data = response.json()
    finally:
        if owns_client:
            await client.aclose()

    return [_parse_element(el) for el in data.get("elements", [])]
