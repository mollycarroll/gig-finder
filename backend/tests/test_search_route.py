from fastapi.testclient import TestClient

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
