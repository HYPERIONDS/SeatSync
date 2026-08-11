from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.database.base import Base, UUIDPrimaryKeyMixin


class PaymentOutcome(StrEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    TIMEOUT = "TIMEOUT"


class PaymentStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class PaymentAttempt(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (Index("ix_payment_booking_created", "booking_id", "created_at"),)

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    requested_outcome: Mapped[PaymentOutcome] = mapped_column(
        Enum(PaymentOutcome, name="payment_outcome"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status"), nullable=False
    )
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Refund(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "refunds"
    __table_args__ = (Index("ix_refunds_booking_created", "booking_id", "created_at"),)

    booking_id: Mapped[UUID] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="SIMULATED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
