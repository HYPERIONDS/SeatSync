from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.events.models import Event
from app.reporting.models import AttendeeExport, ExportStatus
from app.reporting.service import assert_show_owner, dashboard
from app.seat_holds.redis_client import get_redis
from app.users.dependencies import require_roles
from app.users.models import User, UserRole

router = APIRouter(prefix="/organizer", tags=["organizer"])


@router.get("/dashboard")
def organizer_dashboard(
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER, UserRole.ADMIN)),
):
    return dashboard(db, redis, organizer)


@router.post("/shows/{show_id}/attendees/export", status_code=status.HTTP_202_ACCEPTED)
def queue_attendee_export(
    show_id: UUID,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER, UserRole.ADMIN)),
):
    show = assert_show_owner(db, organizer, show_id)
    event = db.get(Event, show.event_id)
    job = AttendeeExport(
        id=uuid4(),
        organizer_id=event.organizer_id,
        show_id=show.id,
        status=ExportStatus.PENDING,
    )
    db.add(job)
    db.commit()
    if get_settings().app_env != "testing":
        from app.reporting.tasks import generate_attendee_export

        generate_attendee_export.delay(str(job.id))
    return {"export_id": job.id, "status": job.status}


@router.get("/exports/{export_id}")
def download_attendee_export(
    export_id: UUID,
    db: Session = Depends(get_db),
    organizer: User = Depends(require_roles(UserRole.ORGANIZER, UserRole.ADMIN)),
):
    job = db.get(AttendeeExport, export_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Export not found")
    if organizer.role is not UserRole.ADMIN and job.organizer_id != organizer.id:
        raise HTTPException(status_code=403, detail="Export belongs to another organizer")
    if job.status != ExportStatus.COMPLETED or not job.file_path:
        return {"export_id": job.id, "status": job.status}
    return FileResponse(
        job.file_path, filename=f"attendees-{job.show_id}.csv", media_type="text/csv"
    )
