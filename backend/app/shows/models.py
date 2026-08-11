from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, UUIDPrimaryKeyMixin
from app.venues.models import SeatCategory


class ShowStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    CANCELLED = "CANCELLED"


class Show(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "shows"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="valid_time_range"),
        Index("ix_shows_start_status", "starts_at", "status"),
        Index("ix_shows_venue_time", "venue_id", "starts_at", "ends_at"),
    )

    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), nullable=False)
    venue_id: Mapped[UUID] = mapped_column(ForeignKey("venues.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[ShowStatus] = mapped_column(
        Enum(ShowStatus, name="show_status"), default=ShowStatus.SCHEDULED, nullable=False
    )
    currency: Mapped[str] = mapped_column(default="INR", nullable=False)
    event: Mapped["Event"] = relationship(back_populates="shows")  # noqa: F821
    venue: Mapped["Venue"] = relationship()  # noqa: F821
    prices: Mapped[list["ShowPrice"]] = relationship(
        back_populates="show", cascade="all, delete-orphan"
    )


class ShowPrice(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "show_prices"
    __table_args__ = (UniqueConstraint("show_id", "category", name="uq_show_price_category"),)

    show_id: Mapped[UUID] = mapped_column(ForeignKey("shows.id", ondelete="CASCADE"))
    category: Mapped[SeatCategory] = mapped_column(
        Enum(SeatCategory, name="seat_category", create_type=False), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    show: Mapped[Show] = relationship(back_populates="prices")
