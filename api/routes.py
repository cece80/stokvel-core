"""
API Routes
===========
Complete API endpoint definitions for the Stokvel platform.

All routes follow REST conventions:
- POST   /resource       → Create
- GET    /resource       → List
- GET    /resource/{id}  → Detail
- PUT    /resource/{id}  → Update
- DELETE /resource/{id}  → Delete

Every authenticated route receives RequestContext with:
- user_id
- organization_id
- role
- permissions

Auth flow:
1. POST /auth/request-otp    → Send OTP
2. POST /auth/verify-otp     → Verify + issue tokens
3. POST /auth/refresh        → Refresh access token
4. POST /auth/logout         → Revoke session
"""


# ──────────────────────────────────────────────
# Route Definitions
# ──────────────────────────────────────────────
#
# Each route is documented with:
# - Method + Path
# - Auth requirement
# - Required permission
# - Input schema
# - Response schema
# - Business logic summary
#
# In production: implement with FastAPI, Express, or NestJS
# ──────────────────────────────────────────────

ROUTES = {

    # ── AUTH ────────────────────────────────
    
    "request_otp": {
        "method": "POST",
        "path": "/auth/request-otp",
        "auth_required": False,
        "input": "RequestOTPInput",
        "response": '{"otp_id": "uuid", "expires_in": 300}',
        "logic": [
            "Validate phone/email format",
            "Check rate limit (max 3 per 10 min)",
            "Generate 6-digit OTP",
            "Hash and store OTP with 5-min expiry",
            "Send via SMS (Twilio/Africa\'s Talking) or email",
            "Return OTP record ID (not the code!)",
        ],
    },
    
    "verify_otp": {
        "method": "POST",
        "path": "/auth/verify-otp",
        "auth_required": False,
        "input": "VerifyOTPInput",
        "response": "AuthResponse",
        "logic": [
            "Look up OTP record",
            "Verify code (constant-time comparison)",
            "If user doesn\'t exist → create user (auto-registration)",
            "Check for new device → require re-verification if needed",
            "Create session (device_id, IP, user_agent)",
            "Enforce session limit (max 5)",
            "Generate access + refresh tokens",
            "Clear failed login attempts",
            "Log auth event in audit",
            "Return tokens + user + requires_onboarding flag",
        ],
    },
    
    "refresh_token": {
        "method": "POST",
        "path": "/auth/refresh",
        "auth_required": False,  # Uses refresh token, not access token
        "input": "RefreshTokenInput",
        "response": "AuthResponse",
        "logic": [
            "Look up session by refresh token hash",
            "Validate session (active, not expired, not revoked)",
            "Rotate refresh token (old one invalidated)",
            "Generate new access token with current org context",
            "Update session last_activity",
            "Return new token pair",
        ],
    },
    
    "logout": {
        "method": "POST",
        "path": "/auth/logout",
        "auth_required": True,
        "input": "LogoutInput",
        "response": '{"success": true, "revoked_count": 1}',
        "logic": [
            "If all_devices=true → revoke all sessions except current",
            "Else → revoke current session only",
            "Log logout event in audit",
        ],
    },

    # ── ORGANIZATION ────────────────────────
    
    "list_organizations": {
        "method": "GET",
        "path": "/organizations",
        "auth_required": True,
        "permission": None,
        "response": "[OrganizationResponse]",
        "logic": [
            "List all organizations the user belongs to",
            "Include role for each org",
            "Include member/stokvel counts",
        ],
    },
    
    "create_organization": {
        "method": "POST",
        "path": "/organizations/create",
        "auth_required": True,
        "permission": None,
        "input": "CreateOrganizationInput",
        "response": "OrganizationResponse",
        "logic": [
            "Validate org name uniqueness",
            "Create organization",
            "Assign creator as org admin",
            "Create default wallet for org",
            "Set as user\'s default org if first",
            "Log in audit",
        ],
    },
    
    "join_organization": {
        "method": "POST",
        "path": "/organizations/join",
        "auth_required": True,
        "permission": None,
        "input": "JoinOrganizationInput",
        "response": "OrganizationResponse",
        "logic": [
            "Validate invite (token or code)",
            "Check invite not expired/used",
            "If phone-targeted → verify user\'s phone matches",
            "Add user to organization with assigned role",
            "Redeem invite (decrement uses)",
            "Log in audit",
        ],
    },
    
    "switch_organization": {
        "method": "POST",
        "path": "/organizations/switch",
        "auth_required": True,
        "input": "SwitchOrganizationInput",
        "response": "AuthResponse",
        "logic": [
            "Verify user belongs to target org",
            "Update session\'s current_organization_id",
            "Issue new access token with updated org context",
            "Return new token + org details",
        ],
    },

    # ── STOKVEL ─────────────────────────────
    
    "create_stokvel": {
        "method": "POST",
        "path": "/stokvels/create",
        "auth_required": True,
        "permission": "org:create_stokvel",
        "input": "CreateStokvelInput",
        "response": "StokvelResponse",
        "logic": [
            "Validate org admin role",
            "Create stokvel with constitution",
            "Assign creator as Chairperson + Signatory",
            "Status = DRAFT",
            "Log in audit",
        ],
    },
    
    "list_stokvels": {
        "method": "GET",
        "path": "/stokvels",
        "auth_required": True,
        "permission": None,
        "response": "[StokvelResponse]",
        "logic": [
            "List stokvels in current organization",
            "Filter by user\'s memberships",
            "Include role and contribution info",
        ],
    },
    
    "invite_stokvel_member": {
        "method": "POST",
        "path": "/stokvels/{id}/invite",
        "auth_required": True,
        "permission": "stokvel:invite_members",
        "input": "InviteMemberInput",
        "response": '{"invite_url": "...", "invite_code": "..."}',
        "logic": [
            "Verify inviter is admin (Chair/Sec/Treas)",
            "Check stokvel hasn\'t hit max members",
            "Generate invite (link + code)",
            "If phone provided → send SMS invite",
            "Log in audit",
        ],
    },
    
    "activate_stokvel": {
        "method": "POST",
        "path": "/stokvels/{id}/activate",
        "auth_required": True,
        "permission": "stokvel:manage",
        "response": "StokvelResponse",
        "logic": [
            "Check min members met (default 3)",
            "Check 3+ signatories assigned",
            "Check Chair + Secretary + Treasurer assigned",
            "Check all signatories KYC verified",
            "Set status = ACTIVE",
            "Log in audit",
        ],
    },

    # ── KYC ──────────────────────────────────
    
    "kyc_status": {
        "method": "GET",
        "path": "/kyc/status",
        "auth_required": True,
        "response": "KYCStatusResponse",
        "logic": [
            "Check user\'s KYC document submissions",
            "Return completeness status",
            "Flag expired proof of address (> 3 months)",
        ],
    },
    
    "submit_kyc_document": {
        "method": "POST",
        "path": "/kyc/submit",
        "auth_required": True,
        "input": "SubmitKYCInput",
        "response": '{"document_id": "...", "status": "submitted"}',
        "logic": [
            "Validate document type",
            "If SA ID → validate 13-digit Luhn",
            "If proof of address → check date < 3 months",
            "Store document reference",
            "Update user kyc_status to DOCUMENTS_SUBMITTED",
            "Log in audit",
        ],
    },

    # ── SESSIONS ─────────────────────────────
    
    "list_sessions": {
        "method": "GET",
        "path": "/sessions",
        "auth_required": True,
        "response": "[SessionResponse]",
        "logic": [
            "List all active sessions for user",
            "Include device name, IP, last activity",
            "Flag current session",
        ],
    },
    
    "revoke_session": {
        "method": "DELETE",
        "path": "/sessions/{id}",
        "auth_required": True,
        "response": '{"success": true}',
        "logic": [
            "Verify session belongs to user",
            "Revoke session (invalidate refresh token)",
            "Log in audit",
        ],
    },

    # ── AUDIT ────────────────────────────────
    
    "audit_log": {
        "method": "GET",
        "path": "/audit-log",
        "auth_required": True,
        "permission": "stokvel:view_audit_log",
        "response": "AuditLogResponse",
        "logic": [
            "Paginated audit log for stokvel",
            "Filter by action type, date range, user",
            "Organization-scoped (multi-tenant isolation)",
        ],
    },
}


def get_route_summary() -> dict:
    """
    Get a summary of all API routes.
    Useful for generating API docs or OpenAPI spec.
    """
    summary = {
        "total_routes": len(ROUTES),
        "public_routes": sum(1 for r in ROUTES.values() if not r.get("auth_required")),
        "authenticated_routes": sum(1 for r in ROUTES.values() if r.get("auth_required")),
        "routes": [],
    }
    
    for name, route in ROUTES.items():
        summary["routes"].append({
            "name": name,
            "method": route["method"],
            "path": route["path"],
            "auth_required": route.get("auth_required", True),
            "permission": route.get("permission"),
        })
    
    return summary
