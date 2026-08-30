from datetime import datetime, timedelta, timezone

from app.models import Area
from app.services.cache import is_stale


def _area(last_scraped_at=None) -> Area:
    return Area(
        query_text="Asheville, NC",
        display_name="Asheville, NC, USA",
        lat=35.5951,
        lon=-82.5515,
        radius_m=10000,
        last_scraped_at=last_scraped_at,
    )


def test_never_scraped_is_stale():
    assert is_stale(_area(last_scraped_at=None)) is True


def test_recently_scraped_is_fresh():
    area = _area(last_scraped_at=datetime.now(timezone.utc) - timedelta(days=1))
    assert is_stale(area) is False


def test_older_than_refresh_window_is_stale():
    area = _area(last_scraped_at=datetime.now(timezone.utc) - timedelta(days=31))
    assert is_stale(area) is True
