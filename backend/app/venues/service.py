from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.users.models import User
from app.venues.models import Seat, Venue, VenueSection
from app.venues.schemas import VenueCreate


def create_venue(db: Session, owner: User, data: VenueCreate) -> Venue:
    venue = Venue(
        id=uuid4(),
        organizer_id=owner.id,
        name=data.name.strip(),
        city=data.city.strip(),
        address=data.address.strip(),
        timezone=data.timezone,
    )
    for section_index, definition in enumerate(data.sections):
        section = VenueSection(name=definition.name.strip(), sort_order=section_index)
        venue.sections.append(section)
        for row in definition.rows:
            for number in range(1, row.seat_count + 1):
                section.seats.append(
                    Seat(
                        venue_id=venue.id,
                        row_label=row.label.upper(),
                        number=number,
                        identifier=f"{definition.name}-{row.label}-{number}".upper(),
                        category=row.category,
                    )
                )
    db.add(venue)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Venue layout contains duplicate seats"
        ) from exc
    return get_venue(db, venue.id)


def get_venue(db: Session, venue_id) -> Venue:
    venue = db.get(
        Venue,
        venue_id,
        options=[selectinload(Venue.sections).selectinload(VenueSection.seats)],
    )
    if venue is None:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue
