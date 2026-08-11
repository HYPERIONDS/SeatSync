from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.users.dependencies import require_roles
from app.users.models import User, UserRole
from app.venues.schemas import VenueCreate, VenueRead
from app.venues.service import create_venue, get_venue

router = APIRouter(prefix="/venues", tags=["venues"])


@router.post("", response_model=VenueRead, status_code=status.HTTP_201_CREATED)
def create(
    data: VenueCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(UserRole.ORGANIZER, UserRole.ADMIN)),
):
    return create_venue(db, user, data)


@router.get("/{venue_id}", response_model=VenueRead)
def read(venue_id: UUID, db: Session = Depends(get_db)):
    return get_venue(db, venue_id)
