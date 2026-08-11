from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.audit.service import record_audit
from app.core.time import utcnow
from app.events.models import Event
from app.shows.models import Show, ShowPrice, ShowStatus
from app.shows.schemas import ShowCreate
from app.users.models import User, UserRole
from app.venues.models import Venue


def create_show(db: Session, event: Event, user: User, data: ShowCreate) -> Show:
    if data.starts_at <= utcnow():
        raise HTTPException(status_code=422, detail="A show must start in the future")
    venue = db.get(Venue, data.venue_id)
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    if user.role is not UserRole.ADMIN and venue.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Venue belongs to another organizer")
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:venue))"), {"venue": str(venue.id)})
    conflict = db.scalar(
        select(Show.id).where(
            Show.venue_id == venue.id,
            Show.status != ShowStatus.CANCELLED,
            Show.starts_at < data.ends_at,
            Show.ends_at > data.starts_at,
        )
    )
    if conflict is not None:
        raise HTTPException(status_code=409, detail="Show overlaps another show at this venue")
    show = Show(
        event_id=event.id,
        venue_id=venue.id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        currency=data.currency.upper(),
        prices=[
            ShowPrice(category=price.category, amount_minor=price.amount_minor)
            for price in data.prices
        ],
    )
    db.add(show)
    db.flush()
    record_audit(
        db,
        user.id,
        "SHOW_CREATED",
        "Show",
        str(show.id),
        {"event_id": str(event.id), "venue_id": str(venue.id)},
    )
    db.commit()
    return db.get(Show, show.id, options=[selectinload(Show.prices)])
