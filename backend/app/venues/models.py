from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.database.base import Base, UUIDPrimaryKeyMixin


class SeatCategory(StrEnum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    VIP = "VIP"


class Venue(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "venues"
    __table_args__ = (Index("ix_venues_city", "city"),)

    organizer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sections: Mapped[list["VenueSection"]] = relationship(
        back_populates="venue", cascade="all, delete-orphan", order_by="VenueSection.name"
    )


class VenueSection(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "venue_sections"
    __table_args__ = (UniqueConstraint("venue_id", "name", name="uq_venue_section_name"),)

    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    venue: Mapped[Venue] = relationship(back_populates="sections")
    seats: Mapped[list["Seat"]] = relationship(
        back_populates="section", cascade="all, delete-orphan", order_by="Seat.identifier"
    )


class Seat(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("venue_id", "identifier", name="uq_seat_venue_identifier"),
        Index("ix_seats_venue_category", "venue_id", "category"),
    )

    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"))
    section_id: Mapped[UUID] = mapped_column(
        ForeignKey("venue_sections.id", ondelete="CASCADE"), nullable=False
    )
    row_label: Mapped[str] = mapped_column(String(16), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    identifier: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[SeatCategory] = mapped_column(
        Enum(SeatCategory, name="seat_category"), nullable=False
    )
    section: Mapped[VenueSection] = relationship(back_populates="seats")
