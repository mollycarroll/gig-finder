import httpx
import pytest

from app.services.geocode import geocode


def _client(response_json):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "Asheville"
        return httpx.Response(200, json=response_json)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_single_match():
    client = _client(
        [
            {
                "place_id": 1,
                "display_name": "Asheville, Buncombe County, North Carolina, USA",
                "lat": "35.5951",
                "lon": "-82.5515",
            }
        ]
    )
    results = await geocode("Asheville", client=client)

    assert len(results) == 1
    assert results[0].place_id == 1
    assert results[0].display_name == "Asheville, Buncombe County, North Carolina, USA"
    assert results[0].lat == pytest.approx(35.5951)
    assert results[0].lon == pytest.approx(-82.5515)


@pytest.mark.asyncio
async def test_multiple_matches():
    client = _client(
        [
            {"place_id": 1, "display_name": "Springfield, IL, USA", "lat": "39.78", "lon": "-89.65"},
            {"place_id": 2, "display_name": "Springfield, MA, USA", "lat": "42.10", "lon": "-72.59"},
            {"place_id": 3, "display_name": "Springfield, MO, USA", "lat": "37.21", "lon": "-93.29"},
        ]
    )
    results = await geocode("Asheville", client=client)

    assert len(results) == 3
    assert {r.place_id for r in results} == {1, 2, 3}


@pytest.mark.asyncio
async def test_no_match():
    client = _client([])
    results = await geocode("Asheville", client=client)

    assert results == []
