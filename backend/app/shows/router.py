from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bookings.models import BookingSeat, BookingSeatStatus
from app.core.time import as_utc, utcnow
from app.database.session import get_db
from app.seat_holds.redis_client import get_redis
from app.shows.models import Show, ShowStatus
from app.venues.models import Seat, VenueSection

router = APIRouter(prefix="/shows", tags=["shows"])


@router.get("/{show_id}/seats")
def seat_map(
    show_id: UUID,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    show = db.get(Show, show_id)
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    seats = db.scalars(
        select(Seat)
        .join(VenueSection, VenueSection.id == Seat.section_id)
        .where(Seat.venue_id == show.venue_id)
        .order_by(VenueSection.sort_order, Seat.row_label, Seat.number)
    ).all()
    booked = set(
        db.scalars(
            select(BookingSeat.seat_id).where(
                BookingSeat.show_id == show.id,
                BookingSeat.status == BookingSeatStatus.CONFIRMED,
            )
        ).all()
    )
    hold_keys = [f"seat:{show.id}:{seat.id}" for seat in seats]
    hold_values = redis.mget(hold_keys) if hold_keys else []
    can_book = show.status == ShowStatus.SCHEDULED and as_utc(show.starts_at) > utcnow()
    items = []
    for seat, hold_id in zip(seats, hold_values, strict=True):
        state = "BOOKED" if seat.id in booked else "HELD" if hold_id else "AVAILABLE"
        items.append(
            {
                "id": seat.id,
                "identifier": seat.identifier,
                "section": seat.section.name,
                "row": seat.row_label,
                "number": seat.number,
                "category": seat.category,
                "state": state,
            }
        )
    return {"show_id": show.id, "bookable": can_book, "seats": items}
