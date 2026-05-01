import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.redis import (
    store_otp, verify_otp, check_rate_limit, increment_otp_attempts, clear_otp_attempts,
    cache_session, invalidate_session, invalidate_all_user_sessions
)
from app.core.security import (
    create_access_token, create_refresh_token, verify_access_token, verify_refresh_token,
    hash_password, verify_password
)
from app.core.email import send_otp_email
from app.core.validation import validate_email
from app.core.exceptions import (
    AuthError, ValidationError, NotFoundError, RateLimitError
)
from app.models.user import User, UserStatus
from app.config import get_settings
import asyncio

# TODO: Replace with real DB
_USERS: Dict[str, User] = {}

class AuthService:
    def __init__(self):
        self.settings = get_settings()
        self.otp_expiry_seconds = self.settings.otp_expiry_seconds
        self.otp_length = self.settings.otp_length
        self.otp_max_attempts = 5
        self.otp_rate_limit = 5
        self.otp_rate_limit_window = 600  # 10 minutes
        self.access_token_expiry = self.settings.access_token_expire_minutes * 60
        self.refresh_token_expiry = self.settings.refresh_token_expire_days * 86400

    async def register_user(self, email: str, password: str, name: str) -> Dict[str, Any]:
        email = validate_email(email)
        rate_key = f"otp:register:rate:{email}"
        allowed, remaining = await check_rate_limit(rate_key, self.otp_rate_limit, self.otp_rate_limit_window)
        if not allowed:
            raise RateLimitError("Too many registration attempts. Please try again later.")
        otp_code = self._generate_otp()
        await store_otp(f"register:{email}", otp_code, self.otp_expiry_seconds)
        await send_otp_email(email, otp_code, "register")
        # Store pending registration (in-memory)
        _USERS[email] = User(
            email=email,
            first_name=name,
            password_hash=hash_password(password),
            status=UserStatus.PENDING_VERIFICATION,
            is_active=False,
        )
        return {"success": True, "message": "OTP sent to email.", "expires_in": self.otp_expiry_seconds}

    async def verify_email(self, email: str, otp: str) -> Dict[str, Any]:
        email = validate_email(email)
        otp_key = f"register:{email}"
        attempts_key = f"register:{email}:attempts"
        attempts = await increment_otp_attempts(attempts_key)
        if attempts > self.otp_max_attempts:
            raise RateLimitError("Too many failed OTP attempts. Please try again later.")
        valid = await verify_otp(otp_key, otp)
        if not valid:
            raise AuthError("Invalid or expired OTP.")
        await clear_otp_attempts(attempts_key)
        user = _USERS.get(email)
        if not user:
            raise NotFoundError("No pending registration found for this email.")
        user.is_active = True
        user.status = UserStatus.ACTIVE
        user.updated_at = datetime.utcnow()
        # TODO: Save to DB
        return {"email": user.email, "first_name": user.first_name, "status": user.status.value}

    async def send_login_otp(self, email: str) -> Dict[str, Any]:
        email = validate_email(email)
        user = _USERS.get(email)
        if not user or not user.is_active:
            raise NotFoundError("User not found or not active.")
        rate_key = f"otp:login:rate:{email}"
        allowed, remaining = await check_rate_limit(rate_key, self.otp_rate_limit, self.otp_rate_limit_window)
        if not allowed:
            raise RateLimitError("Too many login attempts. Please try again later.")
        otp_code = self._generate_otp()
        await store_otp(f"login:{email}", otp_code, self.otp_expiry_seconds)
        await send_otp_email(email, otp_code, "login")
        return {"success": True, "message": "OTP sent to email.", "expires_in": self.otp_expiry_seconds}

    async def verify_login_otp(self, email: str, otp: str) -> Dict[str, Any]:
        email = validate_email(email)
        otp_key = f"login:{email}"
        attempts_key = f"login:{email}:attempts"
        attempts = await increment_otp_attempts(attempts_key)
        if attempts > self.otp_max_attempts:
            raise RateLimitError("Too many failed OTP attempts. Please try again later.")
        valid = await verify_otp(otp_key, otp)
        if not valid:
            raise AuthError("Invalid or expired OTP.")
        await clear_otp_attempts(attempts_key)
        user = _USERS.get(email)
        if not user or not user.is_active:
            raise NotFoundError("User not found or not active.")
        # Issue tokens
        access_token = create_access_token({"sub": user.id, "email": user.email})
        refresh_token = create_refresh_token({"sub": user.id, "email": user.email})
        session_data = {"user_id": user.id, "email": user.email}
        await cache_session(user.id, session_data, self.access_token_expiry)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.access_token_expiry,
            "user": {"email": user.email, "first_name": user.first_name, "status": user.status.value},
        }

    async def send_password_reset_otp(self, email: str) -> Dict[str, Any]:
        email = validate_email(email)
        user = _USERS.get(email)
        if not user or not user.is_active:
            raise NotFoundError("User not found or not active.")
        rate_key = f"otp:forgot:rate:{email}"
        allowed, remaining = await check_rate_limit(rate_key, self.otp_rate_limit, self.otp_rate_limit_window)
        if not allowed:
            raise RateLimitError("Too many password reset attempts. Please try again later.")
        otp_code = self._generate_otp()
        await store_otp(f"forgot:{email}", otp_code, self.otp_expiry_seconds)
        await send_otp_email(email, otp_code, "forgot_password")
        return {"success": True, "message": "OTP sent to email.", "expires_in": self.otp_expiry_seconds}

    async def reset_password(self, email: str, otp: str, new_password: str) -> Dict[str, Any]:
        email = validate_email(email)
        otp_key = f"forgot:{email}"
        attempts_key = f"forgot:{email}:attempts"
        attempts = await increment_otp_attempts(attempts_key)
        if attempts > self.otp_max_attempts:
            raise RateLimitError("Too many failed OTP attempts. Please try again later.")
        valid = await verify_otp(otp_key, otp)
        if not valid:
            raise AuthError("Invalid or expired OTP.")
        await clear_otp_attempts(attempts_key)
        user = _USERS.get(email)
        if not user or not user.is_active:
            raise NotFoundError("User not found or not active.")
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        await invalidate_all_user_sessions(user.id)
        return {"success": True, "message": "Password reset successful."}

    def _generate_otp(self) -> str:
        return ''.join([str(secrets.randbelow(10)) for _ in range(self.otp_length)])

# Singleton instance
auth_service = AuthService()
