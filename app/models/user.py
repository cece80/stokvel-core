import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

# ──────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────

class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"

class KYCStatus(str, Enum):
    NOT_STARTED = "not_started"
    DOCUMENTS_SUBMITTED = "documents_submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"

class StokvelRole(str, Enum):
    CHAIRPERSON = "chairperson"
    SECRETARY = "secretary"
    TREASURER = "treasurer"
    SIGNATORY = "signatory"
    MEMBER = "member"
    OBSERVER = "observer"

class DocumentType(str, Enum):
    SA_ID_DOCUMENT = "sa_id_document"
    SA_ID_CARD = "sa_id_card"
    PASSPORT = "passport"
    PROOF_OF_ADDRESS = "proof_of_address"
    ASYLUM_PERMIT = "asylum_permit"

class StokvelType(str, Enum):
    SAVINGS = "savings"
    BURIAL = "burial"
    INVESTMENT = "investment"
    GROCERY = "grocery"
    ROTATING = "rotating"
    FIXED_INVESTMENT = "fixed"
    INDISHI = "indishi"

# ──────────────────────────────────────────────
# Domain Models
# ──────────────────────────────────────────────

@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    first_name: str = ""
    last_name: str = ""
    email: Optional[str] = None
    phone: str = ""
    sa_id_number: Optional[str] = None
    password_hash: Optional[str] = None
    is_active: bool = True
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    kyc_status: KYCStatus = KYCStatus.NOT_STARTED
    kyc_verified_at: Optional[datetime] = None
    default_organization_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    private_metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_kyc_verified(self) -> bool:
        return self.kyc_status == KYCStatus.VERIFIED

@dataclass
class Organization:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    slug: str = ""
    owner_id: str = ""
    is_active: bool = True
    max_stokvels: int = 50
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class KYCDocument:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    document_type: DocumentType = DocumentType.SA_ID_DOCUMENT
    document_number: Optional[str] = None
    document_url: Optional[str] = None
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    document_date: Optional[date] = None
    expires_at: Optional[date] = None
    submitted_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class OTPRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    otp_code: str = ""
    otp_type: str = "login"
    is_used: bool = False
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

@dataclass
class StokvelMembership:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    stokvel_id: str = ""
    organization_id: str = ""
    role: StokvelRole = StokvelRole.MEMBER
    is_signatory: bool = False
    is_active: bool = True
    joined_at: datetime = field(default_factory=datetime.utcnow)
    invited_by: Optional[str] = None
    contribution_amount: float = 0.0
    total_contributed: float = 0.0

    def is_admin(self) -> bool:
        return self.role in [
            StokvelRole.CHAIRPERSON,
            StokvelRole.SECRETARY,
            StokvelRole.TREASURER,
        ]
