from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
from datetime import date


class Login(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class RefreshToken(BaseModel):
    refresh_token: str


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class ResetPassword(BaseModel):
    new_password: str


class AgeVerificationRequest(BaseModel):
    """Request to verify user's age (COPPA/GDPR compliance)"""
    date_of_birth: date  # ISO format: "YYYY-MM-DD"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "date_of_birth": "2010-01-15"
            }
        }
    )


class AgeVerificationResponse(BaseModel):
    """Response from age verification"""
    success: bool
    age: int
    message: str