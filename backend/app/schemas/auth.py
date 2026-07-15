"""Authentication and user schema definitions."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# Email pattern for validation (avoids requiring email-validator package)
EMAIL_PATTERN = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login."""

    email: str = Field(..., pattern=EMAIL_PATTERN, description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class RegisterRequest(BaseModel):
    """Request body for POST /api/auth/register."""

    email: str = Field(..., pattern=EMAIL_PATTERN, description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    username: str | None = Field(None, max_length=100, description="Optional display username")


class TokenResponse(BaseModel):
    """Response body for successful authentication."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")


class UserResponse(BaseModel):
    """Response body for GET /api/auth/me and user-related endpoints."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")
    username: str | None = Field(None, description="Display username")
    role: str = Field(..., description="User role: admin, supervisor, inspector, viewer")
    is_active: bool = Field(..., description="Whether the account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = ConfigDict(from_attributes=True)
