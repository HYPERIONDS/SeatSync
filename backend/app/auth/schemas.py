from pydantic import BaseModel, EmailStr, Field, field_validator

from app.users.models import UserRole
from app.users.schemas import UserRead


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    full_name: str = Field(min_length=2, max_length=120)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("role")
    @classmethod
    def public_roles_only(cls, value: UserRole) -> UserRole:
        if value is UserRole.ADMIN:
            raise ValueError("ADMIN accounts cannot be self-registered")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead
