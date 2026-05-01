"""
Authentication Module
======================
OTP-based authentication with JWT sessions.
Inspired by Saleor's token-based auth, adapted for SA mobile-first users.

Flow:
1. User enters phone/email
2. System sends OTP (SMS or email)
3. User verifies OTP
4. System issues JWT access + refresh tokens

Security:
- OTP expires after 5 minutes
- Max 3 OTP attempts before lockout
- JWT access token: 15 minutes
- JWT refresh token: 7 days
- Rate limiting on OTP requests
"""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass

from .models import User, OTPRecord, UserStatus


# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_COOLDOWN_SECONDS = 60  # Min time between OTP requests

ACCESS_TOKEN_EXPIRY_MINUTES = 15
REFRESH_TOKEN_EXPIRY_DAYS = 7


# ──────────────────────────────────────────────
# OTP Generation & Verification
# ──────────────────────────────────────────────

def generate_otp(length: int = OTP_LENGTH) -> str:
    """
    Generate a cryptographically secure OTP.
    Uses secrets module for secure random generation.
    """
    return ''.join([str(secrets.randbelow(10)) for _ in range(length)])


def create_otp_record(
    phone: Optional[str] = None,
    email: Optional[str] = None,
    otp_type: str = "login",
    user_id: Optional[str] = None,
) -> OTPRecord:
    """
    Create a new OTP record for verification.
    
    Args:
        phone: User's phone number (E.164 format)
        email: User's email address
        otp_type: Type of OTP (login, registration, password_reset)
        user_id: Associated user ID if known
        
    Returns:
        OTPRecord with generated OTP code
    """
    otp_code = generate_otp()
    
    return OTPRecord(
        user_id=user_id,
        phone=phone,
        email=email,
        otp_code=otp_code,
        otp_type=otp_type,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )


def verify_otp(record: OTPRecord, submitted_code: str) -> Tuple[bool, str]:
    """
    Verify an OTP code against the record.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if already used
    if record.is_used:
        return False, "OTP has already been used"
    
    # Check expiry
    if record.expires_at and datetime.utcnow() > record.expires_at:
        return False, "OTP has expired. Please request a new one"
    
    # Check max attempts
    if record.attempts >= record.max_attempts:
        return False, "Maximum OTP attempts exceeded. Please request a new one"
    
    # Increment attempts
    record.attempts += 1
    
    # Constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(record.otp_code, submitted_code):
        remaining = record.max_attempts - record.attempts
        return False, f"Invalid OTP. {remaining} attempts remaining"
    
    # Mark as used
    record.is_used = True
    return True, "OTP verified successfully"


# ──────────────────────────────────────────────
# JWT Token Management
# ──────────────────────────────────────────────

@dataclass
class TokenPayload:
    """JWT token payload structure."""
    user_id: str
    organization_id: Optional[str] = None
    token_type: str = "access"  # access or refresh
    issued_at: float = 0.0
    expires_at: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "sub": self.user_id,
            "org": self.organization_id,
            "type": self.token_type,
            "iat": self.issued_at,
            "exp": self.expires_at,
        }


def create_token_pair(
    user: User,
    organization_id: Optional[str] = None,
    secret_key: str = "",
) -> dict:
    """
    Create access + refresh token pair.
    
    Inspired by Saleor's create_token pattern.
    In production, use PyJWT or python-jose for actual JWT encoding.
    
    Args:
        user: Authenticated user
        organization_id: Current organization context
        secret_key: JWT signing secret
        
    Returns:
        Dictionary with access_token, refresh_token, and expiry info
    """
    now = time.time()
    
    access_payload = TokenPayload(
        user_id=user.id,
        organization_id=organization_id or user.default_organization_id,
        token_type="access",
        issued_at=now,
        expires_at=now + (ACCESS_TOKEN_EXPIRY_MINUTES * 60),
    )
    
    refresh_payload = TokenPayload(
        user_id=user.id,
        organization_id=organization_id or user.default_organization_id,
        token_type="refresh",
        issued_at=now,
        expires_at=now + (REFRESH_TOKEN_EXPIRY_DAYS * 86400),
    )
    
    # In production: use jwt.encode(payload, secret_key, algorithm="HS256")
    # Placeholder for now - actual JWT library integration needed
    access_token = _encode_token_placeholder(access_payload, secret_key)
    refresh_token = _encode_token_placeholder(refresh_payload, secret_key)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": ACCESS_TOKEN_EXPIRY_MINUTES * 60,
        "user": user.to_dict(),
    }


def _encode_token_placeholder(payload: TokenPayload, secret: str) -> str:
    """
    Placeholder token encoder.
    Replace with jwt.encode() in production using PyJWT.
    
    Example production code:
        import jwt
        return jwt.encode(payload.to_dict(), secret, algorithm="HS256")
    """
    data = str(payload.to_dict())
    signature = hashlib.sha256(f"{data}{secret}".encode()).hexdigest()[:32]
    return f"stokvel.{signature}"


# ──────────────────────────────────────────────
# Auth Flow Orchestration
# ──────────────────────────────────────────────

def initiate_login(phone: str) -> dict:
    """
    Step 1: Initiate OTP login flow.
    
    Args:
        phone: SA phone number
        
    Returns:
        Dict with otp_record_id and message
    """
    from .validators import validate_phone_number
    
    # Validate and normalize phone
    normalized_phone = validate_phone_number(phone)
    
    # Create OTP record
    otp_record = create_otp_record(phone=normalized_phone, otp_type="login")
    
    # In production: send SMS via Twilio, Africa's Talking, or BulkSMS
    # sms_service.send(normalized_phone, f"Your Stokvel OTP: {otp_record.otp_code}")
    
    return {
        "otp_record_id": otp_record.id,
        "phone": normalized_phone,
        "message": "OTP sent successfully",
        "expires_in_seconds": OTP_EXPIRY_MINUTES * 60,
        # NOTE: In production, NEVER return the OTP code
        # This is for development/testing only:
        "_dev_otp": otp_record.otp_code,
    }


def complete_login(
    otp_record: OTPRecord,
    submitted_code: str,
    user: User,
    secret_key: str = "",
) -> dict:
    """
    Step 2: Complete login by verifying OTP and issuing tokens.
    """
    # Verify OTP
    is_valid, message = verify_otp(otp_record, submitted_code)
    
    if not is_valid:
        return {"success": False, "error": message}
    
    # Update user login timestamp
    user.last_login = datetime.utcnow()
    user.status = UserStatus.ACTIVE
    
    # Generate tokens
    tokens = create_token_pair(user, secret_key=secret_key)
    
    return {
        "success": True,
        "message": "Login successful",
        **tokens,
    }
