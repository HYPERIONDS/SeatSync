from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy.orm import Session

from app.bookings.schemas import BookingConfirm, BookingRead
from app.bookings.service import cancel_booking, confirm_booking, list_customer_bookings
from app.database.session import get_db
from app.seat_holds.redis_client import get_redis
from app.users.dependencies import require_roles
from app.users.models import User, UserRole

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/me", response_model=list[BookingRead])
def my_bookings(
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
):
    return list_customer_bookings(db, customer)


@router.post("/{booking_id}/cancel", response_model=BookingRead)
def cancel(
    booking_id: UUID,
    db: Session = Depends(get_db),
    customer: User = Depends(require_roles(UserRole.CUSTOMER, UserRole.ADMIN)),
):
    return cancel_booking(db, customer, booking_id)


@router.post("/confirm")
def confirm(
    data: BookingConfirm,
    idempotency_key: str = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
):
    status_code, body = confirm_booking(db, redis, customer, data, idempotency_key)
    return JSONResponse(status_code=status_code, content=body)
