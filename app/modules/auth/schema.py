from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator


# ── Request schemas ───────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
    tenant_id: str | None = None        # multi-tenant support


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequestSchema(BaseModel):
    email: EmailStr


class PasswordResetConfirmSchema(BaseModel):
    token: str
    new_password: str = Field(min_length=8)
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordResetConfirmSchema":
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=100)
    tenant_id: str | None = None


# ── Response schemas ──────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserAccResponse(BaseModel):
    id: UUID
    username: str
    email: str
    is_active: bool
    is_email_verified: bool
    last_login: datetime | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class LoginLogResponse(BaseModel):
    id: int
    login_type: str | None
    login_status: str | None
    ip_address: str | None
    device_info: str | None
    location: str | None
    created_at: datetime | None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
    detail: Any = None
