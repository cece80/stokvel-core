import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from decimal import Decimal

class StokvelStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISSOLVED = "dissolved"

class ContributionFrequency(str, Enum):
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

class PayoutMethod(str, Enum):
    ROTATING = "rotating"
    END_OF_TERM = "end_of_term"
    ON_DEMAND = "on_demand"
    PROPORTIONAL = "proportional"

@dataclass
class StokvelConstitution:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stokvel_id: str = ""
    min_members: int = 3
    max_members: int = 50
    contribution_amount: Decimal = Decimal("0.00")
    contribution_frequency: ContributionFrequency = ContributionFrequency.MONTHLY
    joining_fee: Decimal = Decimal("0.00")
    late_payment_penalty: Decimal = Decimal("0.00")
    interest_rate: Decimal = Decimal("0.00")
    payout_method: PayoutMethod = PayoutMethod.END_OF_TERM
    min_signatories: int = 3
    withdrawal_approval_count: int = 2
    quorum_percentage: float = 50.0
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    amendment_approval_percentage: float = 75.0
    full_text: str = ""
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None

@dataclass
class Stokvel:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str = ""
    name: str = ""
    slug: str = ""
    description: str = ""
    stokvel_type: str = "savings"
    status: StokvelStatus = StokvelStatus.DRAFT
    nasasa_registered: bool = False
    nasasa_registration_number: Optional[str] = None
    registration_date: Optional[date] = None
    total_pool: Decimal = Decimal("0.00")
    target_amount: Optional[Decimal] = None
    currency: str = "ZAR"
    banks_act_exempt: bool = True
    constitution_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""

    @property
    def is_banks_act_exempt(self) -> bool:
        return self.total_pool < Decimal("100000")

@dataclass
class AuditLogEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stokvel_id: str = ""
    organization_id: str = ""
    user_id: str = ""
    user_role: str = ""
    action: str = ""
    entity_type: str = ""
    entity_id: str = ""
    description: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
