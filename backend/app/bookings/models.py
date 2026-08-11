from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.database.base import Base, UUIDPrimaryKeyMixin
from app.venues.models import SeatCategory


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class BookingSeatStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Booking(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (
        Index("ix_bookings_customer_status", "customer_id", "status"),
        Index("ix_bookings_show_status", "show_id", "status"),
        Index("ix_bookings_organizer_status", "organizer_id", "status"),
    )

    customer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    organizer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    show_id: Mapped[UUID] = mapped_column(ForeignKey("shows.id"), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"), default=BookingStatus.PENDING, nullable=False
    )
    total_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    hold_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seats: Mapped[list["BookingSeat"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )


class BookingSeat(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "booking_seats"

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    show_id: Mapped[UUID] = mapped_column(ForeignKey("shows.id"), nullable=False)
    seat_id: Mapped[UUID] = mapped_column(ForeignKey("seats.id"), nullable=False)
    category: Mapped[SeatCategory] = mapped_column(
        Enum(SeatCategory, name="seat_category", create_type=False), nullable=False
    )
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[BookingSeatStatus] = mapped_column(
        Enum(BookingSeatStatus, name="booking_seat_status"), nullable=False
    )
    booking: Mapped[Booking] = relationship(back_populates="seats")


Index(
    "uq_booking_seat_confirmed",
    BookingSeat.show_id,
    BookingSeat.seat_id,
    unique=True,
    postgresql_where=BookingSeat.status == BookingSeatStatus.CONFIRMED,
    sqlite_where=BookingSeat.status == BookingSeatStatus.CONFIRMED,
)


class IdempotencyRecord(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        Index("uq_idempotency_user_key", "user_id", "key", unique=True),
        Index("ix_idempotency_created", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(120), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
