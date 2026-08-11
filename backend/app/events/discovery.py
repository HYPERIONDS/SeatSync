from datetime import UTC, date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.time import utcnow
from app.events.models import Event
from app.shows.models import Show, ShowStatus
from app.venues.models import Venue


def discover_events(
    db: Session,
    city: str | None,
    event_date: date | None,
    category: str | None,
    page: int,
    page_size: int,
    sort: str,
) -> dict:
    base = (
        select(Event.id, func.min(Show.starts_at).label("next_show"))
        .join(Show, Show.event_id == Event.id)
        .join(Venue, Venue.id == Show.venue_id)
        .where(Show.status == ShowStatus.SCHEDULED, Show.starts_at > utcnow())
        .group_by(Event.id)
    )
    if city:
        base = base.where(func.lower(Venue.city) == city.lower())
    if category:
        base = base.where(func.lower(Event.category) == category.lower())
    if event_date:
        start = datetime.combine(event_date, time.min, tzinfo=UTC)
        base = base.where(Show.starts_at >= start, Show.starts_at < start + timedelta(days=1))
    count = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    order = {
        "date_asc": asc("next_show"),
        "date_desc": desc("next_show"),
        "title_asc": asc(Event.title),
    }[sort]
    rows = db.execute(base.order_by(order).offset((page - 1) * page_size).limit(page_size)).all()
    event_ids = [row.id for row in rows]
    events = db.scalars(select(Event).where(Event.id.in_(event_ids))).all() if event_ids else []
    by_id = {event.id: event for event in events}
    return {
        "items": [
            {
                "id": str(row.id),
                "title": by_id[row.id].title,
                "description": by_id[row.id].description,
                "category": by_id[row.id].category,
                "image_url": by_id[row.id].image_url,
                "next_show": row.next_show,
            }
            for row in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": count,
    }


def event_details(db: Session, event_id) -> dict:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    shows = db.scalars(
        select(Show)
        .where(Show.event_id == event.id, Show.starts_at > utcnow())
        .options(selectinload(Show.prices), selectinload(Show.venue))
        .order_by(Show.starts_at)
    ).all()
    return {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "category": event.category,
        "image_url": event.image_url,
        "shows": [
            {
                "id": show.id,
                "starts_at": show.starts_at,
                "ends_at": show.ends_at,
                "status": show.status,
                "currency": show.currency,
                "prices": show.prices,
                "venue": {
                    "id": show.venue.id,
                    "name": show.venue.name,
                    "city": show.venue.city,
                    "address": show.venue.address,
                },
            }
            for show in shows
        ],
    }
