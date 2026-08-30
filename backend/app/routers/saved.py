import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user_id
from app.db import get_db
from app.models import SavedVenue, Venue
from app.schemas import SavedVenueCreate, SavedVenueOut

router = APIRouter(prefix="/api/saved-venues", tags=["saved-venues"])


@router.get("", response_model=list[SavedVenueOut])
def list_saved_venues(
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> list[SavedVenue]:
    return (
        db.execute(
            select(SavedVenue)
            .options(joinedload(SavedVenue.venue).joinedload(Venue.contact))
            .where(SavedVenue.user_id == user_id)
            .order_by(SavedVenue.created_at.desc())
        )
        .unique()
        .scalars()
        .all()
    )


@router.post("", response_model=SavedVenueOut, status_code=status.HTTP_201_CREATED)
def save_venue(
    body: SavedVenueCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SavedVenue:
    if db.get(Venue, body.venue_id) is None:
        raise HTTPException(status_code=404, detail="Venue not found")

    existing = db.execute(
        select(SavedVenue).where(
            SavedVenue.user_id == user_id, SavedVenue.venue_id == body.venue_id
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing  # idempotent: already saved is not an error

    saved = SavedVenue(user_id=user_id, venue_id=body.venue_id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


@router.delete("/{venue_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_venue(
    venue_id: int,
    user_id: uuid.UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> None:
    saved = db.execute(
        select(SavedVenue).where(
            SavedVenue.user_id == user_id, SavedVenue.venue_id == venue_id
        )
    ).scalar_one_or_none()
    if saved is not None:
        db.delete(saved)
        db.commit()
