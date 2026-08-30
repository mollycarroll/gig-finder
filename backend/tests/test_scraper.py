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
async def test_mailto_contact_link_is_not_fetched_as_a_page():
    # Regression test: a "contact" link that's actually a mailto: address
    # (very common — the anchor/href text matches _CONTACT_LINK_RE) must
    # not be treated as a page to fetch. Handler raises on any request
    # beyond the homepage/robots.txt to prove no second fetch happens.
    client = _client(_allow_robots_then(_read("mailto_contact_link.html")))
    result = await scrape_venue("https://georgiesbunker.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.email == "contact@georgiesbunker.example"


@pytest.mark.asyncio
async def test_script_content_and_url_digits_are_not_extracted():
    # Regression test: a real Squarespace site's client-side form-validation
    # JS embeds the literal string "user@domain.com" as a placeholder in an
    # error message, and its favicon URL contains an 11-digit cache-busting
    # number — both matched our email/phone regexes when we scanned the raw
    # HTML string wholesale. Must only scan visible text + mailto:/tel:.
    client = _client(_allow_robots_then(_read("script_and_url_false_positives.html")))
    result = await scrape_venue("https://capellaon9.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.email is None
    assert result.phone is None


@pytest.mark.asyncio
async def test_adjacent_text_nodes_do_not_fuse():
    # Regression test: a zip code in one <span> immediately followed by an
    # email in a sibling <span>, with no whitespace between them in the
    # markup, must not be joined into "28806contact@...example".
    client = _client(_allow_robots_then(_read("adjacent_text_nodes.html")))
    result = await scrape_venue("https://georgiesbunker.example/", client=client)

    assert result.scrape_status == ScrapeStatus.success
    assert result.email == "contact@georgiesbunker.example"


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
