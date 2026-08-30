from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.db import get_db
from app.models import Area, OsmType, Venue, VenueContact
from app.schemas import GeocodeResult, SearchRequest, SearchResponse, VenueOut
from app.services import cache
from app.services import geocode as geocode_service
from app.services import overpass, scraper
from app.services.overpass import OverpassVenue

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/geocode", response_model=list[GeocodeResult])
async def get_geocode(q: str = Query(..., min_length=1)) -> list[GeocodeResult]:
    candidates = await geocode_service.geocode(q)
    return [
        GeocodeResult(
            place_id=c.place_id, display_name=c.display_name, lat=c.lat, lon=c.lon
        )
        for c in candidates
    ]


@router.post("/search", response_model=SearchResponse)
async def post_search(
    body: SearchRequest, db: Session = Depends(get_db)
) -> SearchResponse:
    # Capped, never rejected — see step-4 decision log.
    radius_m = min(body.radius_m, settings.MAX_SEARCH_RADIUS_M)

    area = _find_or_create_area(db, body, radius_m)

    if cache.is_stale(area):
        try:
            osm_venues = await overpass.find_venues(
                float(area.lat), float(area.lon), area.radius_m
            )
        except httpx.HTTPError:
            raise HTTPException(
                status_code=502,
                detail="Venue lookup failed — try a smaller area.",
            )
        await _rescrape_area(db, area, osm_venues)

    venues = (
        db.execute(
            select(Venue)
            .options(joinedload(Venue.contact))
            .where(Venue.area_id == area.id)
        )
        .unique()
        .scalars()
        .all()
    )

    return SearchResponse(
        area_id=area.id,
        display_name=area.display_name,
        venues=[VenueOut.model_validate(v) for v in venues],
    )


def _get_existing_area(
    db: Session, lat: float, lon: float, radius_m: int
) -> Area | None:
    return db.execute(
        select(Area).where(
            func.round(Area.lat, 4) == round(lat, 4),
            func.round(Area.lon, 4) == round(lon, 4),
            Area.radius_m == radius_m,
        )
    ).scalar_one_or_none()


def _find_or_create_area(db: Session, body: SearchRequest, radius_m: int) -> Area:
    existing = _get_existing_area(db, body.lat, body.lon, radius_m)
    if existing is not None:
        return existing

    area = Area(
        query_text=body.query_text or body.display_name,
        display_name=body.display_name,
        lat=body.lat,
        lon=body.lon,
        radius_m=radius_m,
    )
    db.add(area)
    try:
        db.commit()
    except IntegrityError:
        # Lost the race to a concurrent identical search — use theirs.
        db.rollback()
        existing = _get_existing_area(db, body.lat, body.lon, radius_m)
        assert existing is not None
        return existing

    db.refresh(area)
    return area


async def _rescrape_area(
    db: Session, area: Area, osm_venues: list[OverpassVenue]
) -> None:
    scrape_results = await scraper.scrape_venues([v.website_url for v in osm_venues])

    for osm_venue, scrape_result in zip(osm_venues, scrape_results):
        osm_type = OsmType(osm_venue.osm_type)
        venue = db.execute(
            select(Venue).where(
                Venue.area_id == area.id,
                Venue.osm_id == osm_venue.osm_id,
                Venue.osm_type == osm_type,
            )
        ).scalar_one_or_none()

        if venue is None:
            venue = Venue(area_id=area.id, osm_id=osm_venue.osm_id, osm_type=osm_type)
            db.add(venue)

        venue.name = osm_venue.name
        venue.address = osm_venue.address
        venue.lat = osm_venue.lat
        venue.lon = osm_venue.lon
        venue.website_url = osm_venue.website_url
        venue.osm_phone = osm_venue.osm_phone
        venue.osm_tags = osm_venue.osm_tags
        db.flush()  # populate venue.id for newly-added rows

        contact = db.execute(
            select(VenueContact).where(VenueContact.venue_id == venue.id)
        ).scalar_one_or_none()
        if contact is None:
            contact = VenueContact(venue_id=venue.id)
            db.add(contact)

        contact.email = scrape_result.email
        contact.phone = scrape_result.phone
        contact.social_links = scrape_result.social_links
        contact.booking_url = scrape_result.booking_url
        contact.scrape_status = scrape_result.scrape_status

    area.last_scraped_at = datetime.now(timezone.utc)
    db.commit()
