"""Request/response models for the auth endpoints."""

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.security import MAX_PASSWORD_BYTES
from app.schemas.user import UserRead

MIN_PASSWORD_LENGTH = 8


class _PasswordField(BaseModel):
    password: str = Field(min_length=MIN_PASSWORD_LENGTH)

    @field_validator("password")
    @classmethod
    def _fits_bcrypt(cls, v: str) -> str:
        """bcrypt ignores bytes past 72, which would make two long passwords interchangeable."""
        if len(v.encode()) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")
        return v


class SignupRequest(_PasswordField):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    # Phone stays required and unique, as it is for every user in the data model.
    phone: str = Field(min_length=3, max_length=32)


class LoginRequest(_PasswordField):
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
