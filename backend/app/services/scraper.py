import asyncio
import re
import urllib.robotparser
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from app.config import settings
from app.models import ScrapeStatus

_TIMEOUT = httpx.Timeout(settings.SCRAPE_TIMEOUT_SECONDS)
_USER_AGENT = "gig-finder/1.0 (local dev; respects robots.txt)"

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"\+?1?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")
_CONTACT_LINK_RE = re.compile(r"contact", re.IGNORECASE)
_BOOKING_LINK_RE = re.compile(r"book|ticket|reservation", re.IGNORECASE)
_SOCIAL_DOMAINS = {
    "instagram.com": "instagram",
    "facebook.com": "facebook",
    "twitter.com": "twitter",
    "x.com": "twitter",
}


@dataclass
class ScrapeResult:
    scrape_status: ScrapeStatus
    email: str | None = None
    phone: str | None = None
    social_links: dict[str, str] = field(default_factory=dict)
    booking_url: str | None = None


class _LinkExtractor(HTMLParser):
    """Collects (href, anchor_text) for every <a href="..."> in the page."""

    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._current_href = href
                self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._current_href is not None:
            self.links.append((self._current_href, "".join(self._current_text)))
            self._current_href = None
            self._current_text = []


def _extract_links(html: str) -> list[tuple[str, str]]:
    parser = _LinkExtractor()
    parser.feed(html)
    return parser.links


def _find_link(html: str, base_url: str, pattern: re.Pattern) -> str | None:
    for href, text in _extract_links(html):
        if pattern.search(href) or pattern.search(text):
            return urljoin(base_url, href)
    return None


def _extract_contacts(
    html: str, base_url: str
) -> tuple[str | None, str | None, dict[str, str]]:
    email_match = _EMAIL_RE.search(html)
    email = email_match.group(0) if email_match else None

    phone_match = _PHONE_RE.search(html)
    phone = phone_match.group(0).strip() if phone_match else None

    social_links: dict[str, str] = {}
    for href, _text in _extract_links(html):
        absolute = urljoin(base_url, href)
        host = urlparse(absolute).netloc.lower().removeprefix("www.")
        platform = _SOCIAL_DOMAINS.get(host)
        if platform and platform not in social_links:
            social_links[platform] = absolute

    return email, phone, social_links


async def _robots_allowed(client: httpx.AsyncClient, url: str) -> bool:
    robots_url = urljoin(url, "/robots.txt")
    try:
        response = await client.get(robots_url)
    except httpx.HTTPError:
        return True  # unreachable robots.txt => default allow

    if response.status_code >= 400:
        return True  # no robots.txt => no restrictions

    parser = urllib.robotparser.RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(_USER_AGENT, url)


async def scrape_venue(
    website_url: str | None, client: httpx.AsyncClient | None = None
) -> ScrapeResult:
    """Scrape a venue's homepage (+ one contact page) for booking contact info.

    Never raises for network/parsing failures — every outcome (including
    "no website" and "robots disallowed") is expressed as a scrape_status so
    a search never fails wholesale because one venue's site is unreachable.
    """
    if not website_url:
        return ScrapeResult(scrape_status=ScrapeStatus.no_website)

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(
            timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
        )

    try:
        if not await _robots_allowed(client, website_url):
            return ScrapeResult(scrape_status=ScrapeStatus.disallowed_by_robots)

        try:
            response = await client.get(website_url)
            response.raise_for_status()
        except httpx.TimeoutException:
            return ScrapeResult(scrape_status=ScrapeStatus.timeout)
        except httpx.HTTPError:
            return ScrapeResult(scrape_status=ScrapeStatus.error)

        html = response.text
        email, phone, social_links = _extract_contacts(html, website_url)
        booking_url = _find_link(html, website_url, _BOOKING_LINK_RE)

        contact_page_url = _find_link(html, website_url, _CONTACT_LINK_RE)
        if contact_page_url and contact_page_url != website_url:
            try:
                contact_response = await client.get(contact_page_url)
                contact_response.raise_for_status()
                c_email, c_phone, c_social = _extract_contacts(
                    contact_response.text, contact_page_url
                )
                email = email or c_email
                phone = phone or c_phone
                social_links = {**c_social, **social_links}
                booking_url = booking_url or _find_link(
                    contact_response.text, contact_page_url, _BOOKING_LINK_RE
                )
            except httpx.HTTPError:
                pass  # contact-page fetch failing doesn't fail the whole scrape

        return ScrapeResult(
            scrape_status=ScrapeStatus.success,
            email=email,
            phone=phone,
            social_links=social_links,
            booking_url=booking_url,
        )
    finally:
        if owns_client:
            await client.aclose()


async def scrape_venues(website_urls: list[str | None]) -> list[ScrapeResult]:
    """Scrape multiple venues concurrently, bounded by SCRAPE_CONCURRENCY."""
    semaphore = asyncio.Semaphore(settings.SCRAPE_CONCURRENCY)

    async with httpx.AsyncClient(
        timeout=_TIMEOUT, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
    ) as client:

        async def bound_scrape(url: str | None) -> ScrapeResult:
            async with semaphore:
                return await scrape_venue(url, client=client)

        return await asyncio.gather(*(bound_scrape(url) for url in website_urls))
