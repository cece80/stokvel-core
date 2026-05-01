from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
import bcrypt
from app.config import get_settings

__all__ = [
    "create_access_token",
    "verify_access_token",
    "hash_password",
    "verify_password",
]

def create_access_token(data: dict, expires_in: int = None) -> str:
    """
    Create an access JWT token with HS256 signature.
    Args:
        data: Claims to encode (must be serializable)
        expires_in: Expiry in seconds (default from settings)
    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    secret = settings.jwt_secret
    now = datetime.now(timezone.utc)
    payload = data.copy()
    payload["type"] = "access"
    if expires_in is None:
        expires_in = settings.access_token_expire_minutes * 60
    payload["exp"] = int((now + timedelta(seconds=expires_in)).timestamp())
    payload["iat"] = int(now.timestamp())
    return jwt.encode(payload, secret, algorithm="HS256")

def create_refresh_token(data: dict, expires_in: int = None) -> str:
    settings = get_settings()
    secret = settings.jwt_secret
    now = datetime.now(timezone.utc)
    payload = data.copy()
    payload["type"] = "refresh"
    if expires_in is None:
        expires_in = settings.refresh_token_expire_days * 86400
    payload["exp"] = int((now + timedelta(seconds=expires_in)).timestamp())
    payload["iat"] = int(now.timestamp())
    return jwt.encode(payload, secret, algorithm="HS256")

def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Verify an access JWT token and return the decoded payload.
    Args:
        token: JWT string
    Returns:
        Decoded payload dict
    Raises:
        jwt.ExpiredSignatureError, jwt.InvalidTokenError
    """
    settings = get_settings()
    secret = settings.jwt_secret
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Not an access token")
    except jwt.ExpiredSignatureError as e:
        raise
    except jwt.InvalidTokenError as e:
        raise
    return payload

def verify_refresh_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    secret = settings.jwt_secret
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Not a refresh token")
    except jwt.ExpiredSignatureError as e:
        raise
    except jwt.InvalidTokenError as e:
        raise
    return payload

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    Args:
        password: Plaintext password
    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    Args:
        plain: Plaintext password
        hashed: bcrypt hash string
    Returns:
        True if match, False otherwise
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
