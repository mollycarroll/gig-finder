from pathlib import Path

import httpx
import pytest

from app.models import ScrapeStatus
from app.services.scraper import scrape_venue

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES / name).read_text()


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _allow_robots_then(html: str, path: str = "/"):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == path:
            return httpx.Response(200, text=html)
        raise AssertionError(f"unexpected request to {request.url}")

    return handler


@pytest.mark.asyncio
async def test_no_website():
    result = await scrape_venue(None)
    assert result.scrape_status == ScrapeStatus.no_website
    assert result.email is None


@pytest.mark.asyncio
async def test_has_email():
    client = _client(_allow_robots_then(_read("has_email.html")))
    result = await scrape_venue("https://thebluenote.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.email == "info@thebluenote.example"
    assert result.phone is None
    assert result.booking_url is None


@pytest.mark.asyncio
async def test_has_phone():
    client = _client(_allow_robots_then(_read("has_phone.html")))
    result = await scrape_venue("https://rustyanchor.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.phone == "(555) 867-5309"
    assert result.email is None


@pytest.mark.asyncio
async def test_no_contact_info():
    client = _client(_allow_robots_then(_read("no_contact_info.html")))
    result = await scrape_venue("https://emptyroom.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.email is None
    assert result.phone is None
    assert result.social_links == {}
    assert result.booking_url is None


@pytest.mark.asyncio
async def test_robots_disallowed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /\n")
        raise AssertionError("homepage should not be fetched when robots.txt disallows it")

    client = _client(handler)
    result = await scrape_venue("https://noscrape.example/", client=client)

    assert result.scrape_status == ScrapeStatus.disallowed_by_robots
    assert result.email is None


@pytest.mark.asyncio
async def test_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.TimeoutException("timed out", request=request)

    client = _client(handler)
    result = await scrape_venue("https://slow.example/", client=client)

    assert result.scrape_status == ScrapeStatus.timeout


@pytest.mark.asyncio
async def test_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(500)

    client = _client(handler)
    result = await scrape_venue("https://broken.example/", client=client)

    assert result.scrape_status == ScrapeStatus.error


@pytest.mark.asyncio
async def test_contact_page_merge():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/":
            return httpx.Response(200, text=_read("contact_page_home.html"))
        if request.url.path == "/contact":
            return httpx.Response(200, text=_read("contact_page_contact.html"))
        raise AssertionError(f"unexpected request to {request.url}")

    client = _client(handler)
    result = await scrape_venue("https://wanderingnote.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.email == "booking@wanderingnote.example"
    assert result.booking_url == "https://wanderingnote.example/tickets"
