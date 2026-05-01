
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.models import Invite, User
from app.core.redis import set_invite_token, get_invite_token, delete_invite_token
import secrets
import string

INVITE_EXPIRY_DAYS = 7
INVITE_CODE_LENGTH = 6
MAX_USES_PER_INVITE = 1

class InviteService:
    @staticmethod
    def create_invite(
        organization_id: str,
        created_by: str,
        assigned_role: str = "member",
        invited_email: Optional[str] = None,
        max_uses: int = 1,
        expiry_days: int = INVITE_EXPIRY_DAYS,
    ) -> Dict[str, Any]:
        token = secrets.token_urlsafe(32)
        code = InviteService._generate_invite_code()
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)
        invite = Invite(
            invite_type="organization",
            organization_id=organization_id,
            token=token,
            code=code,
            invited_email=invited_email,
            assigned_role=assigned_role,
            max_uses=max_uses,
            created_by=created_by,
            expires_at=expires_at,
        )
        set_invite_token(token, invite, expires_in=expiry_days * 86400)
        return {"success": True, "invite": invite}

    @staticmethod
    def accept_invite(token: str, user: User) -> Dict[str, Any]:
        invite = get_invite_token(token)
        if not invite:
            return {"success": False, "error": "Invite not found or expired."}
        if not invite.is_valid:
            return {"success": False, "error": "Invite is not valid."}
        if invite.invited_email and invite.invited_email.lower() != user.email.lower():
            return {"success": False, "error": "Invite is for a different email address."}
        invite.current_uses += 1
        if invite.current_uses >= invite.max_uses:
            invite.is_active = False
        delete_invite_token(token)
        # Add user to org (stub)
        return {
            "success": True,
            "organization_id": invite.organization_id,
            "assigned_role": invite.assigned_role,
            "message": "Invite accepted. You have joined the organization.",
        }

    @staticmethod
    def list_pending_invites(user: User) -> List[Invite]:
        # Stub: fetch from DB or Redis
        return []

    @staticmethod
    def _generate_invite_code(length: int = INVITE_CODE_LENGTH) -> str:
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
        return "".join(secrets.choice(chars) for _ in range(length))
