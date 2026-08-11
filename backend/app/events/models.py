from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.database.base import Base, UUIDPrimaryKeyMixin


class Event(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_category", "category"),)

    organizer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    shows: Mapped[list["Show"]] = relationship(back_populates="event")  # noqa: F821
