from uuid import UUID

from fastapi import APIRouter, Depends, status
from redis import Redis
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.seat_holds.redis_client import get_redis
from app.seat_holds.schemas import HoldCreate, HoldRead
from app.seat_holds.service import create_hold, release_hold
from app.users.dependencies import require_roles
from app.users.models import User, UserRole

router = APIRouter(prefix="/holds", tags=["seat holds"])


@router.post("", response_model=HoldRead, status_code=status.HTTP_201_CREATED)
def hold_seats(
    data: HoldCreate,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
):
    return create_hold(db, redis, customer, data)


@router.delete("/{hold_id}", status_code=status.HTTP_204_NO_CONTENT)
def release_seats(
    hold_id: UUID,
    redis: Redis = Depends(get_redis),
    customer: User = Depends(require_roles(UserRole.CUSTOMER)),
):
    release_hold(redis, customer, hold_id)
