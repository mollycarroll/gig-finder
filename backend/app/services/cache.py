from datetime import datetime, timedelta, timezone

from app.config import settings
from app.models import Area


def is_stale(area: Area) -> bool:
    """An Area with no prior scrape, or one older than CACHE_REFRESH_DAYS."""
    if area.last_scraped_at is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.CACHE_REFRESH_DAYS)
    return area.last_scraped_at < cutoff
