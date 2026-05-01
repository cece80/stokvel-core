"""
API Schemas
============
Request and response data structures for all API endpoints.

These are plain dataclass schemas (swap for Pydantic BaseModel
in production for automatic validation).
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────

@dataclass
class RequestOTPInput:
    """POST /auth/request-otp"""
    phone: Optional[str] = None
    email: Optional[str] = None
    # At least one required


@dataclass
class VerifyOTPInput:
    """POST /auth/verify-otp"""
    phone: Optional[str] = None
    email: Optional[str] = None
    otp_code: str = ""
    device_id: Optional[str] = None
    device_name: Optional[str] = None


@dataclass
class RefreshTokenInput:
    """POST /auth/refresh"""
    refresh_token: str = ""


@dataclass
class AuthResponse:
    """Auth success response."""
    success: bool = True
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_in: int = 900  # 15 minutes
    user: dict = field(default_factory=dict)
    organization_id: Optional[str] = None
    requires_onboarding: bool = False


@dataclass
class LogoutInput:
    """POST /auth/logout"""
    session_id: Optional[str] = None     # Logout specific session
    all_devices: bool = False            # Logout all devices


# ──────────────────────────────────────────────
# Organization Schemas
# ──────────────────────────────────────────────

@dataclass
class CreateOrganizationInput:
    """POST /organizations/create"""
    name: str = ""
    slug: Optional[str] = None


@dataclass
class JoinOrganizationInput:
    """POST /organizations/join"""
    invite_token: Optional[str] = None
    invite_code: Optional[str] = None


@dataclass
class SwitchOrganizationInput:
    """POST /organizations/switch"""
    organization_id: str = ""


@dataclass
class OrganizationResponse:
    """Organization details response."""
    id: str = ""
    name: str = ""
    slug: str = ""
    role: str = ""
    member_count: int = 0
    stokvel_count: int = 0
    created_at: str = ""


# ──────────────────────────────────────────────
# Stokvel Schemas
# ──────────────────────────────────────────────

@dataclass
class CreateStokvelInput:
    """POST /stokvels/create"""
    name: str = ""
    stokvel_type: str = "savings"
    description: str = ""
    contribution_amount: float = 0.0
    contribution_frequency: str = "monthly"
    payout_method: str = "end_of_term"
    target_amount: Optional[float] = None
    min_members: int = 3
    max_members: int = 50


@dataclass
class InviteMemberInput:
    """POST /stokvels/{id}/invite"""
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "member"
    is_signatory: bool = False


@dataclass
class AssignRoleInput:
    """PUT /stokvels/{id}/members/{member_id}/role"""
    role: str = ""
    is_signatory: bool = False


@dataclass
class StokvelResponse:
    """Stokvel details response."""
    id: str = ""
    name: str = ""
    stokvel_type: str = ""
    status: str = ""
    member_count: int = 0
    total_pool: float = 0.0
    currency: str = "ZAR"
    your_role: str = ""
    is_signatory: bool = False
    created_at: str = ""


# ──────────────────────────────────────────────
# KYC Schemas
# ──────────────────────────────────────────────

@dataclass
class SubmitKYCInput:
    """POST /kyc/submit"""
    document_type: str = ""      # sa_id_document, passport, proof_of_address
    document_number: Optional[str] = None
    document_url: Optional[str] = None
    document_date: Optional[str] = None  # ISO date for proof of address


@dataclass
class KYCStatusResponse:
    """GET /kyc/status"""
    kyc_status: str = ""
    has_id_document: bool = False
    has_proof_of_address: bool = False
    missing_documents: List[str] = field(default_factory=list)
    is_complete: bool = False


# ──────────────────────────────────────────────
# Session Schemas
# ──────────────────────────────────────────────

@dataclass
class SessionResponse:
    """GET /sessions"""
    id: str = ""
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    last_activity: str = ""
    is_current: bool = False
    created_at: str = ""


# ──────────────────────────────────────────────
# Audit Schemas
# ──────────────────────────────────────────────

@dataclass
class AuditLogResponse:
    """GET /audit-log"""
    entries: List[dict] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    per_page: int = 50
