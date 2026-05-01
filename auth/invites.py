"""
Invite System
==============
Organization and stokvel invitation management.

Methods:
1. Invite link: /join?token=xyz (shareable URL)
2. Invite code: 6-character alphanumeric code
3. Phone invite: Direct phone number invitation

Flow:
1. Admin creates invite (generates token + code)
2. Invitee receives link/code/SMS
3. Invitee clicks link or enters code
4. System validates invite
5. User added to org/stokvel with assigned role
"""

import uuid
import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
from dataclasses import dataclass, field


INVITE_EXPIRY_DAYS = 7
INVITE_CODE_LENGTH = 6
MAX_USES_PER_INVITE = 1  # Default: single use


@dataclass
class Invite:
    """Organization or stokvel invitation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # What is being invited to
    invite_type: str = "organization"  # organization, stokvel
    organization_id: str = ""
    stokvel_id: Optional[str] = None
    
    # Invite credentials
    token: str = ""                     # URL-safe token for link
    code: str = ""                      # Short alphanumeric code
    
    # Target
    invited_phone: Optional[str] = None  # Specific phone number
    invited_email: Optional[str] = None  # Specific email
    assigned_role: str = "member"        # Role to assign on join
    
    # Usage
    max_uses: int = MAX_USES_PER_INVITE
    current_uses: int = 0
    
    # Creator
    created_by: str = ""
    
    # Status
    is_active: bool = True
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=INVITE_EXPIRY_DAYS))
    
    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        return (
            self.is_active
            and not self.is_expired
            and self.current_uses < self.max_uses
        )
    
    @property
    def invite_url(self) -> str:
        if self.invite_type == "organization":
            return f"/join/org?token={self.token}"
        return f"/join/stokvel?token={self.token}"


def _generate_invite_code(length: int = INVITE_CODE_LENGTH) -> str:
    """Generate a short, readable invite code (uppercase + digits)."""
    chars = string.ascii_uppercase + string.digits
    # Remove ambiguous characters
    chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(chars) for _ in range(length))


def create_organization_invite(
    organization_id: str,
    created_by: str,
    assigned_role: str = "member",
    invited_phone: Optional[str] = None,
    invited_email: Optional[str] = None,
    max_uses: int = 1,
    expiry_days: int = INVITE_EXPIRY_DAYS,
) -> Invite:
    """Create an organization invite."""
    return Invite(
        invite_type="organization",
        organization_id=organization_id,
        token=secrets.token_urlsafe(32),
        code=_generate_invite_code(),
        invited_phone=invited_phone,
        invited_email=invited_email,
        assigned_role=assigned_role,
        max_uses=max_uses,
        created_by=created_by,
        expires_at=datetime.utcnow() + timedelta(days=expiry_days),
    )


def create_stokvel_invite(
    organization_id: str,
    stokvel_id: str,
    created_by: str,
    assigned_role: str = "member",
    is_signatory: bool = False,
    invited_phone: Optional[str] = None,
    max_uses: int = 1,
) -> Invite:
    """Create a stokvel invite."""
    invite = Invite(
        invite_type="stokvel",
        organization_id=organization_id,
        stokvel_id=stokvel_id,
        token=secrets.token_urlsafe(32),
        code=_generate_invite_code(),
        invited_phone=invited_phone,
        assigned_role=assigned_role,
        max_uses=max_uses,
        created_by=created_by,
    )
    # Store signatory flag in a way the handler can read
    invite.id = invite.id  # Keep generated ID
    return invite


def validate_invite(
    invite: Invite,
    user_phone: Optional[str] = None,
    user_email: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Validate an invite for use.
    
    Returns:
        (is_valid, error_message)
    """
    if not invite.is_active:
        return False, "This invite has been revoked"
    
    if invite.is_expired:
        return False, "This invite has expired"
    
    if invite.current_uses >= invite.max_uses:
        return False, "This invite has reached its maximum uses"
    
    # If invite is targeted to a specific phone/email, verify
    if invite.invited_phone and user_phone:
        if invite.invited_phone != user_phone:
            return False, "This invite is for a different phone number"
    
    if invite.invited_email and user_email:
        if invite.invited_email.lower() != user_email.lower():
            return False, "This invite is for a different email address"
    
    return True, "Invite valid"


def redeem_invite(invite: Invite) -> dict:
    """Mark an invite as used."""
    invite.current_uses += 1
    
    if invite.current_uses >= invite.max_uses:
        invite.is_active = False
    
    return {
        "success": True,
        "invite_type": invite.invite_type,
        "organization_id": invite.organization_id,
        "stokvel_id": invite.stokvel_id,
        "assigned_role": invite.assigned_role,
        "remaining_uses": max(0, invite.max_uses - invite.current_uses),
    }


def revoke_invite(invite: Invite) -> dict:
    """Revoke an invite (admin action)."""
    invite.is_active = False
    return {
        "success": True,
        "invite_id": invite.id,
        "message": "Invite revoked",
    }
