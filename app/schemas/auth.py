from pydantic import BaseModel, EmailStr, validator, constr
from typing import Optional
import re

# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────

class RequestOTP(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None

    @validator("phone")
    def validate_sa_phone(cls, v):
        if v is None or v == "":
            return v
        # Accepts +27xxxxxxxxx or 0xxxxxxxxx
        if not re.match(r"^(\+27|0)[6-8][0-9]{8}$", v):
            raise ValueError("Invalid South African phone number format")
        return v

class VerifyOTP(BaseModel):
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    otp_code: constr(min_length=4, max_length=8)
    device_id: Optional[str] = None
    device_name: Optional[str] = None

    @validator("phone")
    def validate_sa_phone(cls, v):
        if v is None or v == "":
            return v
        if not re.match(r"^(\+27|0)[6-8][0-9]{8}$", v):
            raise ValueError("Invalid South African phone number format")
        return v

class TokenResponse(BaseModel):
    success: bool = True
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 900
    user: dict
    organization_id: Optional[str] = None
    requires_onboarding: bool = False

class UserProfile(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: str
    kyc_status: str
    created_at: str

    @validator("phone")
    def validate_sa_phone(cls, v):
        if v is None or v == "":
            return v
        if not re.match(r"^(\+27|0)[6-8][0-9]{8}$", v):
            raise ValueError("Invalid South African phone number format")
        return v

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    password: str

    @validator("phone")
    def validate_sa_phone(cls, v):
        if v is None or v == "":
            return v
        if not re.match(r"^(\+27|0)[6-8][0-9]{8}$", v):
            raise ValueError("Invalid South African phone number format")
        return v
