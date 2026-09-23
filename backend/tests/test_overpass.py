from urllib.parse import parse_qs

import httpx
import pytest

from app.services.overpass import OverpassVenue, find_venues, prioritize


@pytest.mark.asyncio
async def test_query_includes_live_music_amenities_and_radius():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"elements": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await find_venues(35.5951, -82.5515, 10000, client=client)

    query = parse_qs(captured["body"])["data"][0]
    assert "around:10000,35.5951,-82.5515" in query
    for amenity in ("bar", "pub", "nightclub", "music_venue"):
        assert amenity in query


@pytest.mark.asyncio
async def test_parses_node_and_way_elements():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "elements": [
                    {
                        "type": "node",
                        "id": 111,
                        "lat": 35.6,
                        "lon": -82.55,
                        "tags": {
                            "name": "The Blue Note",
                            "amenity": "bar",
                            "addr:housenumber": "10",
                            "addr:street": "Main St",
                            "addr:city": "Asheville",
                            "website": "https://thebluenote.example",
                            "phone": "+1 555 867 5309",
                        },
                    },
                    {
                        "type": "way",
                        "id": 222,
                        "center": {"lat": 35.61, "lon": -82.56},
                        "tags": {"amenity": "nightclub"},
                    },
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    venues = await find_venues(35.5951, -82.5515, 10000, client=client)

    assert len(venues) == 2

    node_venue = venues[0]
    assert node_venue.osm_id == 111
    assert node_venue.osm_type == "node"
    assert node_venue.name == "The Blue Note"
    assert node_venue.address == "10 Main St, Asheville"
    assert node_venue.lat == 35.6
    assert node_venue.lon == -82.55
    assert node_venue.website_url == "https://thebluenote.example"
    assert node_venue.osm_phone == "+1 555 867 5309"

    way_venue = venues[1]
    assert way_venue.osm_id == 222
    assert way_venue.osm_type == "way"
    assert way_venue.name == "Unnamed venue"
    assert way_venue.address == ""
    assert way_venue.lat == 35.61
    assert way_venue.lon == -82.56
    assert way_venue.website_url is None
    assert way_venue.osm_phone is None


@pytest.mark.asyncio
async def test_retries_when_server_is_busy():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(504, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"elements": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    venues = await find_venues(35.5951, -82.5515, 10000, client=client)
    assert venues == []
    assert calls["n"] == 3


def _venue(osm_id, website=None, phone=None, address=""):
    return OverpassVenue(
        osm_id=osm_id,
        osm_type="node",
        name=f"V{osm_id}",
        address=address,
        lat=0.0,
        lon=0.0,
        website_url=website,
        osm_phone=phone,
        osm_tags={},
    )


def test_prioritize_prefers_contactable_venues():
    venues = [
        _venue(1),
        _venue(2, phone="555-0100"),
        _venue(3, website="https://a.example"),
        _venue(4, address="1 Main St"),
        _venue(5, website="https://b.example", phone="555-0101"),
    ]
    top = prioritize(venues, 3)
    # Website+phone first, then website-only, then phone-only.
    assert [v.osm_id for v in top] == [5, 3, 2]


def test_prioritize_is_stable_within_ties():
    venues = [_venue(i, website=f"https://v{i}.example") for i in (7, 8, 9)]
    assert [v.osm_id for v in prioritize(venues, 2)] == [7, 8]
