from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
import bcrypt
from app.config import get_settings

__all__ = [
    "create_jwt_token",
    "verify_jwt_token",
    "hash_password",
    "verify_password",
]


def create_jwt_token(payload: dict, expires_in: int = 3600) -> str:
    """
    Create a JWT token with HS256 signature.
    Args:
        payload: Claims to encode (must be serializable)
        expires_in: Expiry in seconds (default 1 hour)
    Returns:
        Encoded JWT string
    """
    settings = get_settings()
    secret = settings.JWT_SECRET
    now = datetime.now(timezone.utc)
    payload = payload.copy()
    payload["exp"] = int((now + timedelta(seconds=expires_in)).timestamp())
    payload["iat"] = int(now.timestamp())
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt_token(token: str) -> Dict[str, Any]:
    """
    Verify a JWT token and return the decoded payload.
    Args:
        token: JWT string
    Returns:
        Decoded payload dict
    Raises:
        jwt.ExpiredSignatureError, jwt.InvalidTokenError
    """
    settings = get_settings()
    secret = settings.JWT_SECRET
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
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


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    Args:
        password: Plaintext password
        hashed: bcrypt hash string
    Returns:
        True if match, False otherwise
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
