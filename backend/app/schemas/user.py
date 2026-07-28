from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.user import UserRole


# ─── Location sub-schema ───────────────────────────────────────────────────────

class LocationBase(BaseModel):
    address: Optional[str] = None
    area: Optional[str] = None
    city: str = "Karachi"
    latitude: float
    longitude: float


class LocationCreate(LocationBase):
    pass


class LocationOut(LocationBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── User schemas ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str
    role: UserRole
    location: Optional[LocationCreate] = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime
    location: Optional[LocationOut] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[LocationCreate] = None


# ─── Auth response ─────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenPayload(BaseModel):
    sub: str        # user id
    role: str
    exp: Optional[int] = None
