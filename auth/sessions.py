"""
Session Management
===================
Multi-device session tracking with secure refresh token rotation.

Architecture:
- Each login creates a Session record tied to device + IP
- Access tokens (15 min) are stateless JWT
- Refresh tokens (7 days) are stored in DB for revocation
- New device detection triggers OTP re-verification
- Session table enables "log out all devices" and audit

Security:
- Refresh tokens hashed before storage (never store plain)
- Device fingerprint tracking
- IP-based anomaly detection
- Concurrent session limits per user
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from dataclasses import dataclass, field


MAX_SESSIONS_PER_USER = 5
REFRESH_TOKEN_EXPIRY_DAYS = 7
SESSION_INACTIVE_TIMEOUT_HOURS = 24


@dataclass
class Session:
    """
    Active user session.
    
    Every login creates a session. Tracks device, IP, and refresh token.
    Enables multi-device management and security monitoring.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    
    # Device info
    device_id: Optional[str] = None        # Client-generated fingerprint
    device_name: Optional[str] = None      # "iPhone 14", "Chrome on Mac"
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Token
    refresh_token_hash: str = ""           # SHA-256 hash of refresh token
    
    # Organization context
    current_organization_id: Optional[str] = None
    
    # Status
    is_active: bool = True
    last_activity: datetime = field(default_factory=datetime.utcnow)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS))
    revoked_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired and self.revoked_at is None


def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token."""
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    """Hash a refresh token for storage. Never store plain tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(
    user_id: str,
    device_id: Optional[str] = None,
    device_name: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    organization_id: Optional[str] = None,
) -> Tuple[Session, str]:
    """
    Create a new session and generate a refresh token.
    
    Returns:
        Tuple of (Session, plain_refresh_token)
        The plain token is returned once to the client, only the hash is stored.
    """
    refresh_token = generate_refresh_token()
    
    session = Session(
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        ip_address=ip_address,
        user_agent=user_agent,
        refresh_token_hash=hash_token(refresh_token),
        current_organization_id=organization_id,
    )
    
    return session, refresh_token


def validate_refresh_token(
    session: Session,
    submitted_token: str,
) -> Tuple[bool, str]:
    """
    Validate a refresh token against its session.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not session.is_active:
        return False, "Session has been revoked"
    
    if session.is_expired:
        return False, "Session has expired. Please log in again"
    
    if session.revoked_at is not None:
        return False, "Session has been revoked"
    
    submitted_hash = hash_token(submitted_token)
    if submitted_hash != session.refresh_token_hash:
        return False, "Invalid refresh token"
    
    return True, "Token valid"


def rotate_refresh_token(session: Session) -> str:
    """
    Rotate the refresh token (issue new one, invalidate old).
    
    Token rotation prevents replay attacks. Each refresh token
    can only be used once.
    
    Returns:
        New plain refresh token
    """
    new_token = generate_refresh_token()
    session.refresh_token_hash = hash_token(new_token)
    session.last_activity = datetime.utcnow()
    # Extend expiry on rotation
    session.expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)
    return new_token


def revoke_session(session: Session) -> dict:
    """Revoke a single session (logout from one device)."""
    session.is_active = False
    session.revoked_at = datetime.utcnow()
    return {
        "success": True,
        "session_id": session.id,
        "message": "Session revoked",
    }


def revoke_all_sessions(
    sessions: List[Session],
    except_session_id: Optional[str] = None,
) -> dict:
    """
    Revoke all sessions for a user (logout from all devices).
    Optionally keep the current session active.
    """
    revoked_count = 0
    for session in sessions:
        if session.id == except_session_id:
            continue
        if session.is_active:
            session.is_active = False
            session.revoked_at = datetime.utcnow()
            revoked_count += 1
    
    return {
        "success": True,
        "revoked_count": revoked_count,
        "message": f"Revoked {revoked_count} sessions",
    }


def check_new_device(
    user_id: str,
    device_id: Optional[str],
    existing_sessions: List[Session],
) -> dict:
    """
    Check if this is a new/unknown device for the user.
    
    If new device detected, require OTP re-verification for security.
    """
    if not device_id:
        return {"is_new_device": True, "requires_reverification": True}
    
    known_devices = {
        s.device_id for s in existing_sessions
        if s.device_id and s.is_active
    }
    
    is_new = device_id not in known_devices
    
    return {
        "is_new_device": is_new,
        "requires_reverification": is_new,
        "known_device_count": len(known_devices),
        "message": "New device detected. OTP verification required." if is_new else "Known device",
    }


def enforce_session_limit(
    sessions: List[Session],
    max_sessions: int = MAX_SESSIONS_PER_USER,
) -> List[Session]:
    """
    Enforce maximum concurrent sessions per user.
    Revoke oldest sessions if limit exceeded.
    
    Returns:
        List of revoked sessions
    """
    active = sorted(
        [s for s in sessions if s.is_active],
        key=lambda s: s.created_at,
    )
    
    revoked = []
    while len(active) > max_sessions:
        oldest = active.pop(0)
        oldest.is_active = False
        oldest.revoked_at = datetime.utcnow()
        revoked.append(oldest)
    
    return revoked


def switch_organization(
    session: Session,
    new_organization_id: str,
) -> dict:
    """
    Switch the active organization context for a session.
    
    Updates the session so the next access token issued
    will contain the new organization_id.
    """
    old_org = session.current_organization_id
    session.current_organization_id = new_organization_id
    session.last_activity = datetime.utcnow()
    
    return {
        "success": True,
        "previous_organization_id": old_org,
        "current_organization_id": new_organization_id,
        "message": "Organization context switched",
    }
