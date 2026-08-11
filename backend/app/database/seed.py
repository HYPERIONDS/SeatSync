from datetime import timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.core.time import utcnow
from app.database.session import SessionLocal
from app.events.models import Event
from app.shows.schemas import PriceCreate, ShowCreate
from app.shows.service import create_show
from app.users.models import User, UserRole
from app.venues.models import SeatCategory
from app.venues.schemas import RowDefinition, SectionDefinition, VenueCreate
from app.venues.service import create_venue

PASSWORD = "SeatSync123!"


def user(db, email: str, full_name: str, role: UserRole) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        return existing
    value = User(
        email=email,
        full_name=full_name,
        role=role,
        password_hash=hash_password(PASSWORD),
    )
    db.add(value)
    db.commit()
    db.refresh(value)
    return value


def run() -> None:
    with SessionLocal() as db:
        user(db, "admin@example.com", "SeatSync Admin", UserRole.ADMIN)
        organizer = user(db, "organizer@example.com", "Demo Organizer", UserRole.ORGANIZER)
        user(db, "customer@example.com", "Demo Customer", UserRole.CUSTOMER)
        existing = db.scalar(select(Event).where(Event.title == "Systems Under the Stars"))
        if existing:
            existing.organizer_id = organizer.id
            for show in existing.shows:
                show.venue.organizer_id = organizer.id
            db.commit()
            print("Seed data already exists; demo ownership is synchronized.")
            return
        venue = create_venue(
            db,
            organizer,
            VenueCreate(
                name="Concurrency Hall",
                city="Bengaluru",
                address="12 Transaction Avenue",
                timezone="Asia/Kolkata",
                sections=[
                    SectionDefinition(
                        name="Orchestra",
                        rows=[
                            RowDefinition(label="A", seat_count=12, category=SeatCategory.VIP),
                            RowDefinition(label="B", seat_count=16, category=SeatCategory.PREMIUM),
                            RowDefinition(label="C", seat_count=20, category=SeatCategory.STANDARD),
                        ],
                    )
                ],
            ),
        )
        event = Event(
            organizer_id=organizer.id,
            title="Systems Under the Stars",
            description=(
                "An evening of live music and engineering stories, used to demonstrate "
                "concurrency-safe ticket booking."
            ),
            category="MUSIC",
        )
        db.add(event)
        db.commit()
        start = utcnow() + timedelta(days=14)
        create_show(
            db,
            event,
            organizer,
            ShowCreate(
                venue_id=venue.id,
                starts_at=start,
                ends_at=start + timedelta(hours=2),
                currency="INR",
                prices=[
                    PriceCreate(category=SeatCategory.STANDARD, amount_minor=75000),
                    PriceCreate(category=SeatCategory.PREMIUM, amount_minor=125000),
                    PriceCreate(category=SeatCategory.VIP, amount_minor=200000),
                ],
            ),
        )
        print("Seeded demo users, venue, event, and show.")


if __name__ == "__main__":
    run()
