from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.database.base import Base, UUIDPrimaryKeyMixin


class ExportStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class AttendeeExport(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "attendee_exports"
    __table_args__ = (Index("ix_exports_organizer_created", "organizer_id", "created_at"),)

    organizer_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    show_id: Mapped[UUID] = mapped_column(ForeignKey("shows.id"), nullable=False)
    status: Mapped[ExportStatus] = mapped_column(
        Enum(ExportStatus, name="export_status"), default=ExportStatus.PENDING, nullable=False
    )
    file_path: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
