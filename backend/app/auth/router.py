from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenPair
from app.auth.service import login, register, rotate_refresh_token
from app.database.session import get_db
from app.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(data: RegisterRequest, db: Session = Depends(get_db)):
    return register(db, data)


@router.post("/login", response_model=TokenPair)
def login_user(data: LoginRequest, db: Session = Depends(get_db)):
    return login(db, data)


@router.post("/refresh", response_model=TokenPair)
def refresh_tokens(data: RefreshRequest, db: Session = Depends(get_db)):
    return rotate_refresh_token(db, data.refresh_token)
