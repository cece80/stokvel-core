"""
Auth Middleware
================
Request authentication and authorization middleware.

Every API request passes through:
1. Extract JWT from Authorization header
2. Verify signature and expiration
3. Extract user context (user_id, organization_id, role)
4. Attach context to request
5. Check route-level permissions

Context Object (attached to every authenticated request):
{
    "user_id": "uuid",
    "organization_id": "uuid",
    "role": "admin",
    "stokvel_id": "uuid" (optional, if in stokvel context),
    "session_id": "uuid",
    "permissions": ["list", "of", "permissions"]
}
"""

import time
import hashlib
from typing import Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum


class AuthError(Exception):
    """Authentication or authorization error."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ──────────────────────────────────────────────
# Request Context
# ──────────────────────────────────────────────

class OrganizationRole(str, Enum):
    """Organization-level roles."""
    ADMIN = "admin"         # Full org management
    MEMBER = "member"       # Participate in stokvels
    SUPPLIER = "supplier"   # Manage products/deals


class PlatformRole(str, Enum):
    """Platform-level roles (super admin)."""
    SUPER_ADMIN = "super_admin"   # Full system control
    SUPPORT = "support"           # View + limited actions
    USER = "user"                 # Regular user (default)


@dataclass
class RequestContext:
    """
    Authentication context attached to every request.
    
    This is the core identity object that flows through the entire
    request lifecycle. Every handler receives this context.
    """
    # Identity
    user_id: str = ""
    session_id: str = ""
    
    # Organization context (multi-tenancy)
    organization_id: Optional[str] = None
    organization_role: OrganizationRole = OrganizationRole.MEMBER
    
    # Stokvel context (optional, set when accessing stokvel routes)
    stokvel_id: Optional[str] = None
    stokvel_role: Optional[str] = None
    
    # Platform role
    platform_role: PlatformRole = PlatformRole.USER
    
    # Computed permissions
    permissions: Set[str] = field(default_factory=set)
    
    # Request metadata
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    
    @property
    def is_org_admin(self) -> bool:
        return self.organization_role == OrganizationRole.ADMIN
    
    @property
    def is_super_admin(self) -> bool:
        return self.platform_role == PlatformRole.SUPER_ADMIN
    
    @property
    def is_supplier(self) -> bool:
        return self.organization_role == OrganizationRole.SUPPLIER
    
    def has_permission(self, permission: str) -> bool:
        if self.is_super_admin:
            return True  # Super admin bypasses all checks
        return permission in self.permissions
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "organization_role": self.organization_role.value,
            "stokvel_id": self.stokvel_id,
            "stokvel_role": self.stokvel_role,
            "platform_role": self.platform_role.value,
            "permissions": list(self.permissions),
        }


# ──────────────────────────────────────────────
# JWT Verification (Middleware Layer 1)
# ──────────────────────────────────────────────

def extract_token(authorization_header: Optional[str]) -> str:
    """
    Extract JWT from Authorization header.
    
    Expected format: "Bearer <token>"
    """
    if not authorization_header:
        raise AuthError("Authorization header missing", 401)
    
    parts = authorization_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Invalid authorization format. Expected: Bearer <token>", 401)
    
    return parts[1]


def verify_token_payload(payload: dict) -> RequestContext:
    """
    Verify JWT payload and build RequestContext.
    
    In production, use PyJWT:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    
    Expected payload:
    {
        "sub": "user_id",
        "org": "organization_id",
        "org_role": "admin",
        "platform_role": "user",
        "sid": "session_id",
        "exp": 1234567890
    }
    """
    # Check expiration
    exp = payload.get("exp", 0)
    if time.time() > exp:
        raise AuthError("Token has expired", 401)
    
    # Check required fields
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("Invalid token: missing user_id", 401)
    
    # Build context
    org_role_str = payload.get("org_role", "member")
    platform_role_str = payload.get("platform_role", "user")
    
    try:
        org_role = OrganizationRole(org_role_str)
    except ValueError:
        org_role = OrganizationRole.MEMBER
    
    try:
        platform_role = PlatformRole(platform_role_str)
    except ValueError:
        platform_role = PlatformRole.USER
    
    return RequestContext(
        user_id=user_id,
        session_id=payload.get("sid", ""),
        organization_id=payload.get("org"),
        organization_role=org_role,
        platform_role=platform_role,
    )


# ──────────────────────────────────────────────
# Organization Isolation (Middleware Layer 2)
# ──────────────────────────────────────────────

def enforce_organization_isolation(
    context: RequestContext,
    requested_org_id: Optional[str] = None,
) -> None:
    """
    Enforce multi-tenant organization isolation.
    
    Core rule: IF request.organization_id != user.organization_id: deny
    
    Super admins can access any organization.
    """
    if context.is_super_admin:
        return  # Super admin bypasses isolation
    
    if not context.organization_id:
        raise AuthError("No organization context. Select an organization first.", 403)
    
    if requested_org_id and requested_org_id != context.organization_id:
        raise AuthError("Access denied: organization mismatch", 403)


# ──────────────────────────────────────────────
# Permission Checks (Middleware Layer 3)
# ──────────────────────────────────────────────

def require_permission(context: RequestContext, permission: str) -> None:
    """Check that the request context has the required permission."""
    if not context.has_permission(permission):
        raise AuthError(
            f"Permission denied: {permission} required",
            403,
        )


def require_org_admin(context: RequestContext) -> None:
    """Require organization admin role."""
    if not context.is_org_admin and not context.is_super_admin:
        raise AuthError("Organization admin access required", 403)


def require_super_admin(context: RequestContext) -> None:
    """Require platform super admin role."""
    if not context.is_super_admin:
        raise AuthError("Super admin access required", 403)


# ──────────────────────────────────────────────
# Route Permission Decorators (for API routes)
# ──────────────────────────────────────────────

# Permission requirements per route pattern
ROUTE_PERMISSIONS = {
    # Auth (public)
    "POST /auth/request-otp": None,
    "POST /auth/verify-otp": None,
    "POST /auth/refresh": None,
    
    # Organization management
    "POST /organizations/create": None,  # Any authenticated user
    "GET /organizations": None,
    "POST /organizations/join": None,
    "PUT /organizations/{id}": "org:manage",
    
    # Stokvel management
    "POST /stokvels/create": "org:create_stokvel",
    "GET /stokvels": None,
    "GET /stokvels/{id}": "stokvel:view",
    "POST /stokvels/{id}/invite": "stokvel:invite_members",
    "POST /stokvels/{id}/roles": "stokvel:manage_roles",
    
    # Contributions
    "POST /contributions": "stokvel:record_contribution",
    "GET /contributions": "stokvel:view_contributions",
    
    # Voting
    "POST /votes/create": "stokvel:create_vote",
    "POST /votes/{id}/cast": "stokvel:cast_vote",
    
    # Admin
    "GET /admin/users": "platform:manage_users",
    "POST /admin/freeze": "platform:freeze_account",
}


# Organization role -> permissions mapping
ORG_ROLE_PERMISSIONS = {
    OrganizationRole.ADMIN: {
        "org:manage", "org:create_stokvel", "org:invite",
        "org:view_members", "org:manage_members",
    },
    OrganizationRole.MEMBER: {
        "org:view_members",
    },
    OrganizationRole.SUPPLIER: {
        "org:manage_products", "org:view_deals",
    },
}


def resolve_permissions(context: RequestContext) -> Set[str]:
    """
    Resolve all permissions for the current request context.
    Combines organization-level + stokvel-level permissions.
    """
    permissions = set()
    
    # Add org-level permissions
    org_perms = ORG_ROLE_PERMISSIONS.get(context.organization_role, set())
    permissions.update(org_perms)
    
    # Stokvel-level permissions would be resolved from
    # the StokvelMembership lookup (see auth/permissions.py)
    
    return permissions
