"""
Auth Models - Inspired by Saleor's account/models.py
=====================================================
Adapted for stokvel-specific requirements including:
- SA ID number as primary identifier
- FICA/KYC verification status tracking
- Stokvel role assignments
- Multi-tenant organization scoping
"""

import uuid
import re
from datetime import datetime, date
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


# ──────────────────────────────────────────────
# Enums (inspired by Saleor's permission/role enums)
# ──────────────────────────────────────────────

class UserStatus(str, Enum):
    """User account status."""
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class KYCStatus(str, Enum):
    """
    KYC/FICA verification status.
    Per FICA (Financial Intelligence Centre Act 38 of 2001),
    all stokvel signatories must be verified.
    """
    NOT_STARTED = "not_started"
    DOCUMENTS_SUBMITTED = "documents_submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"  # Proof of address older than 3 months


class StokvelRole(str, Enum):
    """
    Stokvel member roles.
    Banks (FNB, Absa, Nedbank) require at least 3 elected signatories.
    Standard governance roles for stokvel administration.
    """
    CHAIRPERSON = "chairperson"      # Leads meetings, final authority
    SECRETARY = "secretary"          # Records, communications, minutes
    TREASURER = "treasurer"          # Financial management, contributions
    SIGNATORY = "signatory"          # Bank account signatory (min 3 required)
    MEMBER = "member"                # Regular contributing member
    OBSERVER = "observer"            # Non-contributing, view-only


class DocumentType(str, Enum):
    """Accepted KYC document types per FICA requirements."""
    SA_ID_DOCUMENT = "sa_id_document"        # South African ID book/card
    SA_ID_CARD = "sa_id_card"                # Smart ID card
    PASSPORT = "passport"                     # Valid passport
    PROOF_OF_ADDRESS = "proof_of_address"    # Utility bill, bank statement (< 3 months)
    ASYLUM_PERMIT = "asylum_permit"          # For foreign nationals


class StokvelType(str, Enum):
    """
    Recognized stokvel types in South Africa.
    No formal statutory classification, but these are industry-standard.
    """
    SAVINGS = "savings"              # General savings pool
    BURIAL = "burial"                # Funeral/burial cover
    INVESTMENT = "investment"        # Fixed investment with returns
    GROCERY = "grocery"              # Group grocery purchasing
    ROTATING = "rotating"            # Rotating credit (each member gets lump sum in turn)
    FIXED_INVESTMENT = "fixed"       # Fixed contributions, up to 8% interest
    INDISHI = "indishi"              # Flexible contributions (R50-R3,000), proportional returns


# ──────────────────────────────────────────────
# Core Models
# ──────────────────────────────────────────────

@dataclass
class User:
    """
    Platform user account.
    Inspired by Saleor's User model with SA-specific fields.
    
    Every user belongs to at least one Organization (multi-tenancy).
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Identity
    first_name: str = ""
    last_name: str = ""
    email: Optional[str] = None
    phone: str = ""                      # Primary - most SA users prefer phone
    sa_id_number: Optional[str] = None   # 13-digit SA ID number
    
    # Auth
    password_hash: Optional[str] = None  # For optional password auth
    is_active: bool = True
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    
    # KYC/FICA
    kyc_status: KYCStatus = KYCStatus.NOT_STARTED
    kyc_verified_at: Optional[datetime] = None
    
    # Multi-tenancy
    default_organization_id: Optional[str] = None
    
    # Metadata (Saleor pattern)
    metadata: dict = field(default_factory=dict)
    private_metadata: dict = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_kyc_verified(self) -> bool:
        return self.kyc_status == KYCStatus.VERIFIED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status.value,
            "kyc_status": self.kyc_status.value,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Organization:
    """
    Multi-tenant organization.
    Inspired by Saleor's Channel model for tenant isolation.
    
    Every request must carry organization_id.
    Rule: IF request.organization_id != user.organization_id: deny_access
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    
    # Owner
    owner_id: str = ""
    
    # Settings
    is_active: bool = True
    max_stokvels: int = 50  # Max stokvels per org
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KYCDocument:
    """
    KYC/FICA document submission.
    
    Per FICA requirements for stokvel signatories:
    - Valid SA ID document or passport
    - Proof of residential address (not older than 3 months)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    
    document_type: DocumentType = DocumentType.SA_ID_DOCUMENT
    document_number: Optional[str] = None  # ID number, passport number
    document_url: Optional[str] = None     # Stored document image/PDF
    
    # Verification
    is_verified: bool = False
    verified_by: Optional[str] = None      # Admin who verified
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # For proof of address - must be < 3 months old
    document_date: Optional[date] = None
    expires_at: Optional[date] = None
    
    # Timestamps
    submitted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OTPRecord:
    """OTP verification record for phone/email auth."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    
    otp_code: str = ""
    otp_type: str = "login"  # login, registration, password_reset
    
    is_used: bool = False
    attempts: int = 0
    max_attempts: int = 3
    
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None


@dataclass 
class StokvelMembership:
    """
    Stokvel membership with role assignment.
    
    Banks require at least 3 elected signatories per stokvel.
    Roles: Chairperson, Secretary, Treasurer, Signatory, Member.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    user_id: str = ""
    stokvel_id: str = ""
    organization_id: str = ""
    
    # Role
    role: StokvelRole = StokvelRole.MEMBER
    is_signatory: bool = False  # Bank account signatory
    
    # Status
    is_active: bool = True
    joined_at: datetime = field(default_factory=datetime.utcnow)
    invited_by: Optional[str] = None
    
    # Contribution tracking
    contribution_amount: float = 0.0  # Monthly/weekly contribution
    total_contributed: float = 0.0
    
    def is_admin(self) -> bool:
        """Check if member has admin privileges."""
        return self.role in [
            StokvelRole.CHAIRPERSON,
            StokvelRole.SECRETARY,
            StokvelRole.TREASURER,
        ]
