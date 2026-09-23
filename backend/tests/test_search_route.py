from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import Area

from app.models import ScrapeStatus
from app.services.overpass import OverpassVenue
from app.services.scraper import ScrapeResult

SEARCH_BODY = {
    "lat": 35.5951,
    "lon": -82.5515,
    "display_name": "Asheville, NC, USA",
    "query_text": "asheville",
    "radius_m": 10000,
}


def _mock_overpass(monkeypatch, venues):
    async def fake_find_venues(lat, lon, radius_m, client=None):
        return venues

    monkeypatch.setattr("app.routers.search.overpass.find_venues", fake_find_venues)


def _mock_scraper(monkeypatch, results):
    calls = []

    async def fake_scrape_venues(urls):
        calls.append(urls)
        return results

    monkeypatch.setattr("app.routers.search.scraper.scrape_venues", fake_scrape_venues)
    return calls


def _fail_if_called(monkeypatch, target):
    async def fail(*args, **kwargs):
        raise AssertionError(f"{target} should not have been called on a cache hit")

    monkeypatch.setattr(target, fail)


def test_cache_miss_scrapes_and_creates_area(client: TestClient, monkeypatch):
    osm_venue = OverpassVenue(
        osm_id=1,
        osm_type="node",
        name="The Blue Note",
        address="1 Main St, Asheville",
        lat=35.6,
        lon=-82.55,
        website_url="https://thebluenote.example",
        osm_phone=None,
        osm_tags={"amenity": "bar"},
    )
    _mock_overpass(monkeypatch, [osm_venue])
    _mock_scraper(
        monkeypatch,
        [ScrapeResult(scrape_status=ScrapeStatus.success, email="info@thebluenote.example")],
    )

    response = client.post("/api/search", json=SEARCH_BODY)

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Asheville, NC, USA"
    assert len(data["venues"]) == 1
    venue = data["venues"][0]
    assert venue["name"] == "The Blue Note"
    assert venue["contact"]["email"] == "info@thebluenote.example"
    assert venue["contact"]["scrape_status"] == "success"


def test_cache_hit_does_not_rescrape(client: TestClient, monkeypatch):
    osm_venue = OverpassVenue(
        osm_id=2,
        osm_type="node",
        name="The Rusty Anchor",
        address="",
        lat=35.6,
        lon=-82.55,
        website_url=None,
        osm_phone=None,
        osm_tags={},
    )
    _mock_overpass(monkeypatch, [osm_venue])
    _mock_scraper(monkeypatch, [ScrapeResult(scrape_status=ScrapeStatus.no_website)])

    first = client.post("/api/search", json=SEARCH_BODY)
    assert first.status_code == 200
    area_id = first.json()["area_id"]

    # Now make a second identical search fail loudly if it re-hits either
    # external service — a cache hit must skip both entirely.
    _fail_if_called(monkeypatch, "app.routers.search.overpass.find_venues")
    _fail_if_called(monkeypatch, "app.routers.search.scraper.scrape_venues")

    second = client.post("/api/search", json=SEARCH_BODY)

    assert second.status_code == 200
    assert second.json()["area_id"] == area_id
    assert second.json()["venues"] == first.json()["venues"]


def test_radius_is_clamped_not_rejected(client: TestClient, monkeypatch):
    _mock_overpass(monkeypatch, [])
    _mock_scraper(monkeypatch, [])

    body = {**SEARCH_BODY, "lat": 31.0, "lon": -99.0, "radius_m": 500_000}
    response = client.post("/api/search", json=body)

    assert response.status_code == 200
    assert response.json()["venues"] == []


def test_query_text_defaults_to_display_name(client: TestClient, monkeypatch):
    _mock_overpass(monkeypatch, [])
    _mock_scraper(monkeypatch, [])

    body = {k: v for k, v in SEARCH_BODY.items() if k != "query_text"}
    body = {**body, "lat": 40.0, "lon": -100.0}
    response = client.post("/api/search", json=body)

    assert response.status_code == 200


def test_geocode_route(client: TestClient, monkeypatch):
    from app.services.geocode import GeocodeCandidate

    async def fake_geocode(query, client=None):
        assert query == "Asheville"
        return [GeocodeCandidate(place_id=1, display_name="Asheville, NC, USA", lat=35.6, lon=-82.55)]

    monkeypatch.setattr("app.routers.search.geocode_service.geocode", fake_geocode)

    response = client.get("/api/geocode", params={"q": "Asheville"})

    assert response.status_code == 200
    assert response.json() == [
        {"place_id": 1, "display_name": "Asheville, NC, USA", "lat": 35.6, "lon": -82.55}
    ]


def _osm_venue(osm_id, website=None, phone=None):
    return OverpassVenue(
        osm_id=osm_id,
        osm_type="node",
        name=f"Venue {osm_id}",
        address="",
        lat=35.6,
        lon=-82.55,
        website_url=website,
        osm_phone=phone,
        osm_tags={"amenity": "bar"},
    )


def _mock_overpass_failure(monkeypatch):
    async def fail(lat, lon, radius_m, client=None):
        raise httpx.ConnectError("overpass unreachable")

    monkeypatch.setattr("app.routers.search.overpass.find_venues", fail)


def test_large_search_is_capped_and_prioritized(client: TestClient, monkeypatch):
    # 14 venues with no contact hints plus one with a website; the default
    # 10km radius counts as large, so only 10 venues survive and the
    # website-carrying one must be among them.
    venues = [_osm_venue(i) for i in range(1, 15)] + [
        _osm_venue(99, website="https://best.example")
    ]
    _mock_overpass(monkeypatch, venues)
    calls = _mock_scraper(
        monkeypatch, [ScrapeResult(scrape_status=ScrapeStatus.no_website)] * 10
    )

    body = {**SEARCH_BODY, "lat": 36.0001, "display_name": "Big Town"}
    response = client.post("/api/search", json=body)

    assert response.status_code == 200
    returned = response.json()["venues"]
    assert len(returned) == 10
    assert "Venue 99" in [v["name"] for v in returned]
    assert len(calls[0]) == 10  # only the capped list was scraped


def test_small_search_is_not_capped(client: TestClient, monkeypatch):
    venues = [_osm_venue(i) for i in range(1, 15)]
    _mock_overpass(monkeypatch, venues)
    _mock_scraper(
        monkeypatch, [ScrapeResult(scrape_status=ScrapeStatus.no_website)] * 14
    )

    body = {**SEARCH_BODY, "lat": 36.0002, "display_name": "Small Town", "radius_m": 3000}
    response = client.post("/api/search", json=body)

    assert response.status_code == 200
    assert len(response.json()["venues"]) == 14


def test_overpass_failure_serves_cached_results(
    client: TestClient, db_session, monkeypatch
):
    body = {**SEARCH_BODY, "lat": 36.5, "display_name": "Fallback Town"}
    _mock_overpass(monkeypatch, [_osm_venue(1, website="https://a.example")])
    _mock_scraper(
        monkeypatch,
        [ScrapeResult(scrape_status=ScrapeStatus.success, email="x@a.example")],
    )
    assert client.post("/api/search", json=body).status_code == 200

    # Age the cache so the next search re-queries Overpass, then break Overpass.
    area = db_session.execute(
        select(Area).where(Area.display_name == "Fallback Town")
    ).scalar_one()
    area.last_scraped_at = datetime.now(timezone.utc) - timedelta(days=999)
    db_session.commit()
    _mock_overpass_failure(monkeypatch)

    response = client.post("/api/search", json=body)

    assert response.status_code == 200
    returned = response.json()["venues"]
    assert len(returned) == 1
    assert returned[0]["contact"]["email"] == "x@a.example"


def test_overpass_failure_with_no_cache_is_502(client: TestClient, monkeypatch):
    _mock_overpass_failure(monkeypatch)

    body = {**SEARCH_BODY, "lat": 36.6, "display_name": "No Cache Town"}
    response = client.post("/api/search", json=body)

    assert response.status_code == 502
