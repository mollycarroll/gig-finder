import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class OsmType(str, enum.Enum):
    node = "node"
    way = "way"
    relation = "relation"


class ScrapeStatus(str, enum.Enum):
    success = "success"
    no_website = "no_website"
    timeout = "timeout"
    disallowed_by_robots = "disallowed_by_robots"
    error = "error"


class Area(Base):
    __tablename__ = "area"
    __table_args__ = (
        # Functional unique index — round(numeric, int) requires Numeric
        # (not Float) columns; Postgres has no round(double precision, int)
        # two-arg overload.
        Index(
            "ix_area_dedupe",
            text("round(lat, 4)"),
            text("round(lon, 4)"),
            "radius_m",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    query_text: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    lon: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    radius_m: Mapped[int] = mapped_column(Integer, nullable=False)
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    venues: Mapped[list["Venue"]] = relationship(
        back_populates="area", cascade="all, delete-orphan", passive_deletes=True
    )


class Venue(Base):
    __tablename__ = "venue"
    __table_args__ = (
        # Upsert key for re-scrapes: OSM ids aren't unique across element
        # types, so osm_type is part of the constraint alongside osm_id.
        UniqueConstraint("area_id", "osm_id", "osm_type", name="uq_venue_area_osm"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    area_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("area.id", ondelete="CASCADE"), nullable=False
    )
    osm_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    osm_type: Mapped[OsmType] = mapped_column(
        SQLEnum(OsmType, name="osm_type"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    lon: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True)
    osm_phone: Mapped[str | None] = mapped_column(String, nullable=True)
    osm_tags: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    area: Mapped["Area"] = relationship(back_populates="venues")
    contact: Mapped["VenueContact | None"] = relationship(
        back_populates="venue",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    saved_by: Mapped[list["SavedVenue"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan", passive_deletes=True
    )


class VenueContact(Base):
    __tablename__ = "venue_contact"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    venue_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("venue.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    social_links: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    booking_url: Mapped[str | None] = mapped_column(String, nullable=True)
    scrape_status: Mapped[ScrapeStatus] = mapped_column(
        SQLEnum(ScrapeStatus, name="scrape_status"), nullable=False
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    venue: Mapped["Venue"] = relationship(back_populates="contact")


class SavedVenue(Base):
    __tablename__ = "saved_venue"
    __table_args__ = (
        UniqueConstraint("user_id", "venue_id", name="uq_saved_venue_user_venue"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # Supabase auth.users id — no DB-level FK (auth schema isn't managed by
    # our Alembic migrations); enforced at the app layer by auth.py instead.
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    venue_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("venue.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    venue: Mapped["Venue"] = relationship(back_populates="saved_by")
