from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import ScrapeStatus


class GeocodeResult(BaseModel):
    place_id: int
    display_name: str
    lat: float
    lon: float


class SearchRequest(BaseModel):
    lat: float
    lon: float
    display_name: str
    query_text: str | None = None
    radius_m: int = 10000


class VenueContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str | None
    phone: str | None
    social_links: dict[str, str]
    booking_url: str | None
    scrape_status: ScrapeStatus


class VenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    address: str
    lat: float
    lon: float
    website_url: str | None
    osm_phone: str | None
    contact: VenueContactOut | None = None


class SearchResponse(BaseModel):
    area_id: int
    display_name: str
    venues: list[VenueOut]


class SavedVenueCreate(BaseModel):
    venue_id: int


class SavedVenueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    venue_id: int
    created_at: datetime
    venue: VenueOut
