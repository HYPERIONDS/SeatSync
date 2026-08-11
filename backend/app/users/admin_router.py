from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database.session import get_db
from app.users.dependencies import require_roles
from app.users.models import User, UserRole
from app.users.schemas import RoleUpdate, UserRead

router = APIRouter(prefix="/admin/users", tags=["administration"])


@router.patch("/{user_id}/role", response_model=UserRead)
def update_role(
    user_id: UUID,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    previous = target.role
    target.role = data.role
    record_audit(
        db,
        admin.id,
        "USER_ROLE_CHANGED",
        "User",
        str(target.id),
        {"previous_role": previous.value, "new_role": data.role.value},
    )
    db.commit()
    return target
