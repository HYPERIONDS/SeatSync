from datetime import date
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.events.discovery import discover_events, event_details
from app.events.models import Event
from app.events.schemas import EventCreate, EventRead
from app.shows.schemas import ShowCreate, ShowRead
from app.shows.service import create_show
from app.users.dependencies import require_roles
from app.users.models import User, UserRole

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def browse_events(
    city: str | None = None,
    date_filter: date | None = None,
    category: str | None = None,
    page: int = 1,
    page_size: int = 12,
    sort: Literal["date_asc", "date_desc", "title_asc"] = "date_asc",
    db: Session = Depends(get_db),
):
    if page < 1 or not 1 <= page_size <= 100:
        raise HTTPException(status_code=422, detail="Invalid pagination")
    return discover_events(db, city, date_filter, category, page, page_size, sort)


@router.get("/{event_id}")
def read_event(event_id: UUID, db: Session = Depends(get_db)):
    return event_details(db, event_id)


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ORGANIZER, UserRole.ADMIN)),
):
    event = Event(organizer_id=user.id, **data.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.post("/{event_id}/shows", response_model=ShowRead, status_code=status.HTTP_201_CREATED)
def add_show(
    event_id: UUID,
    data: ShowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ORGANIZER, UserRole.ADMIN)),
):
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    if user.role is not UserRole.ADMIN and event.organizer_id != user.id:
        raise HTTPException(status_code=403, detail="Event belongs to another organizer")
    return create_show(db, event, user, data)
