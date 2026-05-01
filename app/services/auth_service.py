
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from app.core.redis import store_otp, verify_otp as redis_verify_otp, check_rate_limit
from app.core.security import create_token, verify_token, hash_password
from app.core.email import send_otp_email
from app.models import User, OTPRecord, Session

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RATE_LIMIT = 5  # max 5 OTPs
OTP_RATE_LIMIT_WINDOW = 900  # 15 minutes in seconds
ACCESS_TOKEN_EXPIRY_MINUTES = 15
REFRESH_TOKEN_EXPIRY_DAYS = 7

class AuthService:
    @staticmethod
    def register(email: str) -> Dict[str, Any]:
        # Rate limit OTP requests
        if not check_rate_limit(f"otp:email:{email}", OTP_RATE_LIMIT, OTP_RATE_LIMIT_WINDOW):
            return {"success": False, "error": "Too many OTP requests. Please try again later."}
        
        otp_code = AuthService._generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        store_otp(email=email, otp_code=otp_code, expires_at=expires_at, otp_type="register")
        send_otp_email(email, otp_code)
        return {
            "success": True,
            "message": "OTP sent to email.",
            "expires_in": OTP_EXPIRY_MINUTES * 60,
        }

    @staticmethod
    def login(email: str) -> Dict[str, Any]:
        if not check_rate_limit(f"otp:email:{email}", OTP_RATE_LIMIT, OTP_RATE_LIMIT_WINDOW):
            return {"success": False, "error": "Too many OTP requests. Please try again later."}
        otp_code = AuthService._generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        store_otp(email=email, otp_code=otp_code, expires_at=expires_at, otp_type="login")
        send_otp_email(email, otp_code)
        return {
            "success": True,
            "message": "OTP sent to email.",
            "expires_in": OTP_EXPIRY_MINUTES * 60,
        }

    @staticmethod
    def verify_otp(email: str, otp_code: str, otp_type: str = "login") -> Dict[str, Any]:
        result = redis_verify_otp(email=email, otp_code=otp_code, otp_type=otp_type, max_attempts=OTP_MAX_ATTEMPTS)
        if not result["success"]:
            return result
        # Fetch user from DB (stub)
        user = User.get_by_email(email)
        if not user:
            return {"success": False, "error": "User not found."}
        # Issue tokens
        tokens = AuthService._issue_tokens(user)
        return {"success": True, **tokens}

    @staticmethod
    def refresh_token(refresh_token: str) -> Dict[str, Any]:
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            return {"success": False, "error": "Invalid or expired refresh token."}
        user = User.get_by_id(payload["sub"])
        if not user:
            return {"success": False, "error": "User not found."}
        tokens = AuthService._issue_tokens(user)
        return {"success": True, **tokens}

    @staticmethod
    def forgot_password(email: str) -> Dict[str, Any]:
        if not check_rate_limit(f"otp:email:{email}", OTP_RATE_LIMIT, OTP_RATE_LIMIT_WINDOW):
            return {"success": False, "error": "Too many OTP requests. Please try again later."}
        otp_code = AuthService._generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
        store_otp(email=email, otp_code=otp_code, expires_at=expires_at, otp_type="forgot_password")
        send_otp_email(email, otp_code)
        return {
            "success": True,
            "message": "OTP sent to email.",
            "expires_in": OTP_EXPIRY_MINUTES * 60,
        }

    @staticmethod
    def reset_password(email: str, otp_code: str, new_password: str) -> Dict[str, Any]:
        result = redis_verify_otp(email=email, otp_code=otp_code, otp_type="forgot_password", max_attempts=OTP_MAX_ATTEMPTS)
        if not result["success"]:
            return result
        user = User.get_by_email(email)
        if not user:
            return {"success": False, "error": "User not found."}
        user.password_hash = hash_password(new_password)
        user.save()
        return {"success": True, "message": "Password reset successful."}

    @staticmethod
    def _generate_otp(length: int = 6) -> str:
        import secrets
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

    @staticmethod
    def _issue_tokens(user: User) -> Dict[str, Any]:
        now = datetime.utcnow()
        access_token = create_token(
            user_id=user.id,
            token_type="access",
            expires_at=now + timedelta(minutes=ACCESS_TOKEN_EXPIRY_MINUTES)
        )
        refresh_token = create_token(
            user_id=user.id,
            token_type="refresh",
            expires_at=now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
        )
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": ACCESS_TOKEN_EXPIRY_MINUTES * 60,
            "user": user.to_dict(),
        }
