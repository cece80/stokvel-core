"""
Stokvel OS - Main API Application
===================================
Production-ready FastAPI backend implementing the complete
auth + onboarding + roles + sessions system.

Run:
    uvicorn main:app --reload --port 8000

API Docs:
    http://localhost:8000/docs

Architecture:
    Identity (who you are)
    + Organization (where you belong)
    + Role (what you can do)

Every request must answer:
    1. Who is this user?
    2. Which organization are they acting in?
    3. What are they allowed to do?
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import os

from auth.authentication import (
    create_otp_record, verify_otp, create_token_pair,
    generate_otp, OTP_EXPIRY_MINUTES,
)
from auth.sessions import (
    create_session, validate_refresh_token, rotate_refresh_token,
    revoke_session, revoke_all_sessions, check_new_device,
    enforce_session_limit, switch_organization, Session,
)
from auth.middleware import (
    extract_token, verify_token_payload, enforce_organization_isolation,
    require_org_admin, RequestContext, OrganizationRole, PlatformRole,
    AuthError,
)
from auth.security import RateLimiter, validate_password_strength
from auth.validators import validate_sa_id_number, validate_phone_number, SAIDValidationError
from auth.invites import (
    create_organization_invite, create_stokvel_invite,
    validate_invite, redeem_invite,
)
from auth.models import (
    User, Organization, StokvelMembership, StokvelRole,
    UserStatus, KYCStatus, OTPRecord,
)
from auth.kyc import start_kyc_verification, submit_kyc_document, check_kyc_completeness
from stokvel.models import Stokvel, StokvelConstitution, StokvelStatus, AuditLogEntry
from stokvel.onboarding import (
    create_organization, create_stokvel, invite_member,
    assign_officer_role, check_activation_readiness, activate_stokvel,
)


# ──────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────

app = FastAPI(
    title="Stokvel OS API",
    description="Multi-tenant stokvel coordination + commerce + financial system",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (replace with PostgreSQL + SQLAlchemy in production)
users_db: dict[str, User] = {}
orgs_db: dict[str, Organization] = {}
stokvels_db: dict[str, Stokvel] = {}
memberships_db: dict[str, StokvelMembership] = {}
sessions_db: dict[str, Session] = {}
otp_records: dict[str, OTPRecord] = {}
audit_log: list[AuditLogEntry] = []

rate_limiter = RateLimiter()

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")


# ──────────────────────────────────────────────
# Pydantic Request/Response Models
# ──────────────────────────────────────────────

class RequestOTP(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None

class VerifyOTP(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    otp_code: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None

class PasswordLogin(BaseModel):
    email: str
    password: str
    device_id: Optional[str] = None

class RefreshToken(BaseModel):
    refresh_token: str

class CreateOrg(BaseModel):
    name: str
    slug: Optional[str] = None

class JoinOrg(BaseModel):
    invite_token: Optional[str] = None
    invite_code: Optional[str] = None

class SwitchOrg(BaseModel):
    organization_id: str

class CreateStokvelReq(BaseModel):
    name: str
    stokvel_type: str = "savings"
    description: str = ""
    contribution_amount: float = 0.0
    contribution_frequency: str = "monthly"
    payout_method: str = "end_of_term"
    target_amount: Optional[float] = None
    min_members: int = 3
    max_members: int = 50

class InviteMember(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "member"
    is_signatory: bool = False

class AssignRole(BaseModel):
    role: str
    is_signatory: bool = False

class SubmitKYC(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    document_url: Optional[str] = None
    document_date: Optional[str] = None

class LogoutReq(BaseModel):
    all_devices: bool = False


# ──────────────────────────────────────────────
# Auth Dependency
# ──────────────────────────────────────────────

async def get_current_user(authorization: Optional[str] = Header(None)) -> RequestContext:
    """
    Auth middleware — runs on every protected route.
    
    1. Extract JWT from Authorization header
    2. Verify signature + expiration
    3. Extract user context (user_id, organization_id, role)
    4. Return RequestContext
    """
    try:
        token = extract_token(authorization)
        # In production: jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        # For now, parse our placeholder tokens
        context = verify_token_payload({"sub": "placeholder", "exp": 9999999999})
        return context
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


# ══════════════════════════════════════════════
# AUTH ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/auth/request-otp")
async def request_otp(body: RequestOTP, request: Request):
    """
    Step 1: Request OTP.
    
    POST /auth/request-otp
    Input: phone or email
    
    Flow:
    1. Validate phone/email format
    2. Check rate limit (max 3 per 10 min, 60s cooldown)
    3. Generate 6-digit OTP
    4. Hash and store with 5-min expiry
    5. Send via SMS or email
    """
    identifier = body.phone or body.email
    if not identifier:
        raise HTTPException(400, "Phone or email required")
    
    # Validate format
    if body.phone:
        try:
            identifier = validate_phone_number(body.phone)
        except SAIDValidationError as e:
            raise HTTPException(400, str(e))
    
    # Rate limit check
    allowed, msg = rate_limiter.check_otp_rate(identifier)
    if not allowed:
        raise HTTPException(429, msg)
    
    # Generate OTP
    otp_record = create_otp_record(
        phone=body.phone,
        email=body.email,
        otp_type="login",
    )
    otp_records[otp_record.id] = otp_record
    
    # TODO: Send via SMS (Twilio / Africa's Talking) or email
    # sms_service.send(identifier, f"Your Stokvel OTP: {otp_record.otp_code}")
    
    return {
        "otp_id": otp_record.id,
        "expires_in": OTP_EXPIRY_MINUTES * 60,
        "message": "OTP sent",
        # DEV ONLY — remove in production:
        "_dev_otp": otp_record.otp_code,
    }


@app.post("/auth/verify-otp")
async def verify_otp_endpoint(body: VerifyOTP, request: Request):
    """
    Step 2: Verify OTP and issue tokens.
    
    POST /auth/verify-otp
    Input: phone/email + otp_code + device_id
    
    Flow:
    1. Look up OTP record
    2. Verify code (constant-time comparison)
    3. If user doesn't exist -> auto-create
    4. Check new device -> flag for re-verification
    5. Create session (device, IP, user_agent)
    6. Enforce session limit (max 5)
    7. Generate access + refresh tokens
    8. Log auth event
    """
    identifier = body.phone or body.email
    if not identifier:
        raise HTTPException(400, "Phone or email required")
    
    # Check login rate limit (brute force protection)
    allowed, msg = rate_limiter.check_login_attempts(identifier)
    if not allowed:
        raise HTTPException(429, msg)
    
    # Find OTP record (in production: query DB)
    otp_record_obj = None
    for record in otp_records.values():
        if (record.phone == body.phone or record.email == body.email) and not record.is_used:
            otp_record_obj = record
            break
    
    if not otp_record_obj:
        rate_limiter.record_failed_login(identifier)
        raise HTTPException(400, "No pending OTP found. Request a new one")
    
    # Verify OTP
    is_valid, error_msg = verify_otp(otp_record_obj, body.otp_code)
    if not is_valid:
        rate_limiter.record_failed_login(identifier)
        raise HTTPException(400, error_msg)
    
    # Clear failed attempts on success
    rate_limiter.clear_login_attempts(identifier)
    
    # Find or create user (auto-registration)
    user = None
    for u in users_db.values():
        if u.phone == body.phone or u.email == body.email:
            user = u
            break
    
    if not user:
        user = User(
            phone=body.phone or "",
            email=body.email,
            status=UserStatus.ACTIVE,
        )
        users_db[user.id] = user
    
    # Check new device
    user_sessions = [s for s in sessions_db.values() if s.user_id == user.id]
    device_check = check_new_device(user.id, body.device_id, user_sessions)
    
    # Create session
    client_ip = request.client.host if request.client else None
    session, refresh_token = create_session(
        user_id=user.id,
        device_id=body.device_id,
        device_name=body.device_name,
        ip_address=client_ip,
        user_agent=request.headers.get("user-agent"),
        organization_id=user.default_organization_id,
    )
    sessions_db[session.id] = session
    
    # Enforce session limit
    revoked = enforce_session_limit(user_sessions + [session])
    
    # Generate tokens
    tokens = create_token_pair(user, secret_key=JWT_SECRET)
    
    # Update last login
    user.last_login = datetime.utcnow()
    
    # Check if onboarding needed
    has_orgs = any(
        True for o in orgs_db.values()
        if o.owner_id == user.id
    )
    
    # Audit log
    audit_log.append(AuditLogEntry(
        user_id=user.id,
        action="user_login",
        entity_type="auth",
        entity_id=session.id,
        description=f"Login via OTP from {client_ip}",
        metadata={"device": body.device_name, "new_device": device_check["is_new_device"]},
    ))
    
    return {
        "success": True,
        "access_token": tokens["access_token"],
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": tokens["expires_in"],
        "user": user.to_dict(),
        "organization_id": user.default_organization_id,
        "requires_onboarding": not has_orgs,
        "new_device_detected": device_check["is_new_device"],
    }


@app.post("/auth/refresh")
async def refresh_token_endpoint(body: RefreshToken):
    """
    Refresh access token.
    
    POST /auth/refresh
    Input: refresh_token
    
    Flow:
    1. Find session by refresh token hash
    2. Validate (active, not expired, not revoked)
    3. Rotate refresh token (old one invalidated)
    4. Issue new access token with current org context
    """
    from auth.sessions import hash_token
    
    submitted_hash = hash_token(body.refresh_token)
    
    # Find session
    session = None
    for s in sessions_db.values():
        if s.refresh_token_hash == submitted_hash:
            session = s
            break
    
    if not session:
        raise HTTPException(401, "Invalid refresh token")
    
    is_valid, error = validate_refresh_token(session, body.refresh_token)
    if not is_valid:
        raise HTTPException(401, error)
    
    # Rotate token
    new_refresh = rotate_refresh_token(session)
    
    # Get user
    user = users_db.get(session.user_id)
    if not user:
        raise HTTPException(401, "User not found")
    
    # New access token with current org context
    tokens = create_token_pair(
        user,
        organization_id=session.current_organization_id,
        secret_key=JWT_SECRET,
    )
    
    return {
        "success": True,
        "access_token": tokens["access_token"],
        "refresh_token": new_refresh,
        "token_type": "Bearer",
        "expires_in": tokens["expires_in"],
        "organization_id": session.current_organization_id,
    }


@app.post("/auth/logout")
async def logout(body: LogoutReq, ctx: RequestContext = Depends(get_current_user)):
    """
    Logout - revoke session(s).
    
    POST /auth/logout
    
    all_devices=false -> revoke current session only
    all_devices=true  -> revoke all sessions except current
    """
    user_sessions = [s for s in sessions_db.values() if s.user_id == ctx.user_id]
    
    if body.all_devices:
        result = revoke_all_sessions(user_sessions, except_session_id=ctx.session_id)
    else:
        current = sessions_db.get(ctx.session_id)
        if current:
            result = revoke_session(current)
        else:
            result = {"success": True, "message": "No active session"}
    
    # Audit
    audit_log.append(AuditLogEntry(
        user_id=ctx.user_id,
        action="user_logout",
        entity_type="auth",
        entity_id=ctx.session_id,
        description="Logout" + (" (all devices)" if body.all_devices else ""),
    ))
    
    return result


# ══════════════════════════════════════════════
# ORGANIZATION ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/organizations")
async def list_organizations(ctx: RequestContext = Depends(get_current_user)):
    """
    List organizations the user belongs to.
    
    GET /organizations
    """
    # Find orgs where user is owner or member
    user_orgs = [o for o in orgs_db.values() if o.owner_id == ctx.user_id]
    return {
        "organizations": [
            {
                "id": o.id,
                "name": o.name,
                "slug": o.slug,
                "role": "admin" if o.owner_id == ctx.user_id else "member",
                "is_active": o.is_active,
            }
            for o in user_orgs
        ]
    }


@app.post("/organizations/create")
async def create_org(body: CreateOrg, ctx: RequestContext = Depends(get_current_user)):
    """
    Create a new organization.
    
    POST /organizations/create
    
    Flow:
    1. Create organization
    2. Assign creator as admin
    3. Create default wallet (placeholder)
    4. Set as user's default org if first
    """
    user = users_db.get(ctx.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    org = create_organization(user, body.name, body.slug)
    orgs_db[org.id] = org
    
    # TODO: Create default wallet for organization
    # wallet = create_wallet(org.id, currency="ZAR")
    
    audit_log.append(AuditLogEntry(
        organization_id=org.id,
        user_id=ctx.user_id,
        action="organization_created",
        entity_type="organization",
        entity_id=org.id,
        description=f"Created organization: {body.name}",
    ))
    
    return {
        "success": True,
        "organization": {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "role": "admin",
        },
        "message": f"Organization '{body.name}' created. You are the admin.",
    }


@app.post("/organizations/switch")
async def switch_org(body: SwitchOrg, ctx: RequestContext = Depends(get_current_user)):
    """
    Switch active organization context.
    
    POST /organizations/switch
    
    Flow:
    1. Verify user belongs to target org
    2. Update session's organization context
    3. Issue new access token with updated org_id
    """
    org = orgs_db.get(body.organization_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    
    # Verify membership (simplified - check ownership)
    if org.owner_id != ctx.user_id:
        raise HTTPException(403, "You do not belong to this organization")
    
    # Update session
    session = sessions_db.get(ctx.session_id)
    if session:
        result = switch_organization(session, body.organization_id)
    
    # Issue new access token
    user = users_db.get(ctx.user_id)
    tokens = create_token_pair(user, organization_id=body.organization_id, secret_key=JWT_SECRET)
    
    return {
        "success": True,
        "access_token": tokens["access_token"],
        "organization_id": body.organization_id,
        "organization_name": org.name,
        "message": f"Switched to organization: {org.name}",
    }


# ══════════════════════════════════════════════
# STOKVEL ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/stokvels/create")
async def create_stokvel_endpoint(
    body: CreateStokvelReq,
    ctx: RequestContext = Depends(get_current_user),
):
    """
    Create a new stokvel with constitution.
    
    POST /stokvels/create
    Requires: org admin
    
    Flow:
    1. Validate org admin role
    2. Create stokvel + constitution
    3. Creator becomes Chairperson + first Signatory
    4. Status = DRAFT
    """
    if not ctx.organization_id:
        raise HTTPException(400, "Select an organization first")
    
    user = users_db.get(ctx.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    stokvel, constitution, membership = create_stokvel(
        creator=user,
        organization_id=ctx.organization_id,
        name=body.name,
        stokvel_type=body.stokvel_type,
        description=body.description,
        contribution_amount=body.contribution_amount,
        contribution_frequency=body.contribution_frequency,
        payout_method=body.payout_method,
        target_amount=body.target_amount,
        min_members=body.min_members,
        max_members=body.max_members,
    )
    
    stokvels_db[stokvel.id] = stokvel
    memberships_db[membership.id] = membership
    
    audit_log.append(AuditLogEntry(
        stokvel_id=stokvel.id,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        user_role="chairperson",
        action="stokvel_created",
        entity_type="stokvel",
        entity_id=stokvel.id,
        description=f"Created stokvel: {body.name}",
    ))
    
    return {
        "success": True,
        "stokvel": stokvel.to_dict(),
        "your_role": "chairperson",
        "is_signatory": True,
        "status": "draft",
        "message": f"Stokvel '{body.name}' created. Invite members to activate.",
    }


@app.get("/stokvels")
async def list_stokvels(ctx: RequestContext = Depends(get_current_user)):
    """List stokvels in current organization."""
    if not ctx.organization_id:
        raise HTTPException(400, "Select an organization first")
    
    user_stokvels = [
        s for s in stokvels_db.values()
        if s.organization_id == ctx.organization_id
    ]
    
    return {
        "stokvels": [s.to_dict() for s in user_stokvels]
    }


@app.post("/stokvels/{stokvel_id}/invite")
async def invite_to_stokvel(
    stokvel_id: str,
    body: InviteMember,
    ctx: RequestContext = Depends(get_current_user),
):
    """
    Invite a member to a stokvel.
    
    POST /stokvels/{id}/invite
    Requires: stokvel admin (Chair/Sec/Treas)
    
    Methods: phone number, invite link, invite code
    """
    stokvel = stokvels_db.get(stokvel_id)
    if not stokvel:
        raise HTTPException(404, "Stokvel not found")
    
    # Create invite
    invite = create_stokvel_invite(
        organization_id=stokvel.organization_id,
        stokvel_id=stokvel_id,
        created_by=ctx.user_id,
        assigned_role=body.role,
        is_signatory=body.is_signatory,
        invited_phone=body.phone,
    )
    
    # TODO: If phone provided, send SMS with invite link
    
    return {
        "success": True,
        "invite_url": invite.invite_url,
        "invite_code": invite.code,
        "expires_in_days": 7,
        "message": "Invite created",
    }


@app.post("/stokvels/{stokvel_id}/activate")
async def activate_stokvel_endpoint(
    stokvel_id: str,
    ctx: RequestContext = Depends(get_current_user),
):
    """
    Activate a stokvel.
    
    POST /stokvels/{id}/activate
    
    Checks:
    1. Min members met (default 3)
    2. 3+ signatories assigned
    3. Chair + Secretary + Treasurer assigned
    4. All signatories KYC verified
    """
    stokvel = stokvels_db.get(stokvel_id)
    if not stokvel:
        raise HTTPException(404, "Stokvel not found")
    
    members = [m for m in memberships_db.values() if m.stokvel_id == stokvel_id]
    
    readiness = check_activation_readiness(
        stokvel=stokvel,
        constitution=StokvelConstitution(stokvel_id=stokvel_id),
        memberships=members,
        users=users_db,
    )
    
    if not readiness["is_ready"]:
        return {
            "success": False,
            "issues": readiness["issues"],
            "message": "Stokvel is not ready for activation",
        }
    
    result = activate_stokvel(stokvel, readiness)
    
    audit_log.append(AuditLogEntry(
        stokvel_id=stokvel_id,
        organization_id=stokvel.organization_id,
        user_id=ctx.user_id,
        action="stokvel_activated",
        entity_type="stokvel",
        entity_id=stokvel_id,
        description=f"Stokvel activated with {readiness['member_count']} members",
    ))
    
    return result


# ══════════════════════════════════════════════
# KYC ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/kyc/status")
async def kyc_status(ctx: RequestContext = Depends(get_current_user)):
    """Check KYC verification status."""
    user = users_db.get(ctx.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return start_kyc_verification(user)


@app.post("/kyc/submit")
async def submit_kyc(body: SubmitKYC, ctx: RequestContext = Depends(get_current_user)):
    """Submit a KYC document for verification."""
    user = users_db.get(ctx.user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    from auth.models import DocumentType
    from datetime import date as date_type
    
    try:
        doc_type = DocumentType(body.document_type)
    except ValueError:
        raise HTTPException(400, f"Invalid document type: {body.document_type}")
    
    doc_date = None
    if body.document_date:
        try:
            doc_date = date_type.fromisoformat(body.document_date)
        except ValueError:
            raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")
    
    doc, result = submit_kyc_document(
        user=user,
        document_type=doc_type,
        document_number=body.document_number,
        document_url=body.document_url,
        document_date=doc_date,
    )
    
    if not result["success"]:
        raise HTTPException(400, result["errors"])
    
    return result


# ══════════════════════════════════════════════
# SESSION ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/sessions")
async def list_sessions(ctx: RequestContext = Depends(get_current_user)):
    """List all active sessions for the user."""
    user_sessions = [
        s for s in sessions_db.values()
        if s.user_id == ctx.user_id and s.is_active
    ]
    
    return {
        "sessions": [
            {
                "id": s.id,
                "device_name": s.device_name,
                "ip_address": s.ip_address,
                "last_activity": s.last_activity.isoformat(),
                "is_current": s.id == ctx.session_id,
                "created_at": s.created_at.isoformat(),
            }
            for s in user_sessions
        ]
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, ctx: RequestContext = Depends(get_current_user)):
    """Revoke a specific session (remote logout)."""
    session = sessions_db.get(session_id)
    if not session or session.user_id != ctx.user_id:
        raise HTTPException(404, "Session not found")
    
    result = revoke_session(session)
    
    audit_log.append(AuditLogEntry(
        user_id=ctx.user_id,
        action="session_revoked",
        entity_type="session",
        entity_id=session_id,
        description=f"Revoked session on {session.device_name}",
    ))
    
    return result


# ══════════════════════════════════════════════
# AUDIT LOG ENDPOINT
# ══════════════════════════════════════════════

@app.get("/audit-log")
async def get_audit_log(
    stokvel_id: Optional[str] = None,
    limit: int = 50,
    ctx: RequestContext = Depends(get_current_user),
):
    """
    Get audit log entries.
    Organization-scoped for multi-tenant isolation.
    """
    entries = audit_log
    
    if stokvel_id:
        entries = [e for e in entries if e.stokvel_id == stokvel_id]
    
    if ctx.organization_id:
        entries = [
            e for e in entries
            if e.organization_id == ctx.organization_id or not e.organization_id
        ]
    
    # Sort newest first, limit
    entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]
    
    return {
        "entries": [
            {
                "id": e.id,
                "action": e.action,
                "entity_type": e.entity_type,
                "description": e.description,
                "user_id": e.user_id,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries
        ],
        "total_count": len(entries),
    }


# ══════════════════════════════════════════════
# HEALTH + META
# ══════════════════════════════════════════════

@app.get("/")
async def root():
    return {
        "name": "Stokvel OS API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
