from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.bookings.models import BookingSeatStatus, BookingStatus
from app.payments.models import PaymentOutcome, PaymentStatus
from app.venues.models import SeatCategory


class BookingConfirm(BaseModel):
    hold_id: UUID
    payment_outcome: PaymentOutcome = PaymentOutcome.SUCCESS


class BookingSeatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    seat_id: UUID
    category: SeatCategory
    price_minor: int
    status: BookingSeatStatus


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    show_id: UUID
    status: BookingStatus
    total_minor: int
    currency: str
    created_at: datetime
    confirmed_at: datetime | None
    cancelled_at: datetime | None
    seats: list[BookingSeatRead]


class ConfirmationResult(BaseModel):
    booking: BookingRead
    payment_status: PaymentStatus
    replayed: bool = False
    message: str
