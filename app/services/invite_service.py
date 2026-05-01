import secrets
import string
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app.models.user import User
from app.core.redis import cache_set, cache_get, cache_delete

INVITE_EXPIRY_DAYS = 7
INVITE_CODE_LENGTH = 6
MAX_USES_PER_INVITE = 1

# TODO: Replace with DB-backed Invite model
class Invite:
    def __init__(self, invite_type, organization_id, token, code, invited_email, assigned_role, max_uses, created_by, expires_at):
        self.invite_type = invite_type
        self.organization_id = organization_id
        self.token = token
        self.code = code
        self.invited_email = invited_email
        self.assigned_role = assigned_role
        self.max_uses = max_uses
        self.current_uses = 0
        self.created_by = created_by
        self.expires_at = expires_at
        self.is_active = True
        self.is_valid = True

class InviteService:
    @staticmethod
    async def create_invite(
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
        await cache_set(f"invite:{token}", invite.__dict__, expiry_days * 86400)
        return {"success": True, "invite": invite.__dict__}

    @staticmethod
    async def accept_invite(token: str, user: User) -> Dict[str, Any]:
        invite_data = await cache_get(f"invite:{token}")
        if not invite_data:
            return {"success": False, "error": "Invite not found or expired."}
        if not invite_data.get("is_valid", True):
            return {"success": False, "error": "Invite is not valid."}
        if invite_data.get("invited_email") and invite_data["invited_email"].lower() != user.email.lower():
            return {"success": False, "error": "Invite is for a different email address."}
        invite_data["current_uses"] = invite_data.get("current_uses", 0) + 1
        if invite_data["current_uses"] >= invite_data["max_uses"]:
            invite_data["is_active"] = False
        await cache_delete(f"invite:{token}")
        # Add user to org (stub)
        return {
            "success": True,
            "organization_id": invite_data["organization_id"],
            "assigned_role": invite_data["assigned_role"],
            "message": "Invite accepted. You have joined the organization.",
        }

    @staticmethod
    async def list_pending_invites(user: User) -> List[dict]:
        # Stub: fetch from DB or Redis
        return []

    @staticmethod
    def _generate_invite_code(length: int = INVITE_CODE_LENGTH) -> str:
        chars = string.ascii_uppercase + string.digits
        chars = chars.replace("0", "").replace("O", "").replace("I", "").replace("1", "")
        return "".join(secrets.choice(chars) for _ in range(length))
