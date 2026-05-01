"""
Stokvel Models
===============
Core stokvel entity models including constitution and governance structure.

Based on Saleor's product/channel patterns, adapted for stokvel operations.
"""

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from dataclasses import dataclass, field


class StokvelStatus(str, Enum):
    """Stokvel lifecycle status."""
    DRAFT = "draft"                    # Being set up
    PENDING_APPROVAL = "pending"       # Awaiting NASASA or internal approval
    ACTIVE = "active"                  # Operational
    SUSPENDED = "suspended"            # Temporarily suspended
    DISSOLVED = "dissolved"            # Permanently closed


class ContributionFrequency(str, Enum):
    """How often members contribute."""
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class PayoutMethod(str, Enum):
    """How funds are distributed."""
    ROTATING = "rotating"              # Each member gets lump sum in turn
    END_OF_TERM = "end_of_term"       # All members paid at term end
    ON_DEMAND = "on_demand"            # Withdrawals with approval
    PROPORTIONAL = "proportional"      # Based on contribution ratio


@dataclass
class StokvelConstitution:
    """
    Stokvel constitution/rules document.
    
    While not legally required, recommended governance includes:
    - Membership rules
    - Contribution amounts and frequency
    - Officer roles and elections
    - Withdrawal/payout rules
    - Dispute resolution
    - Amendment process
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stokvel_id: str = ""
    
    # Core rules
    min_members: int = 3               # Minimum to operate
    max_members: int = 50              # Practical limit
    contribution_amount: float = 0.0   # Fixed contribution per period
    contribution_frequency: ContributionFrequency = ContributionFrequency.MONTHLY
    
    # Financial rules
    joining_fee: float = 0.0
    late_payment_penalty: float = 0.0
    interest_rate: float = 0.0         # Up to 8% for fixed investment
    payout_method: PayoutMethod = PayoutMethod.END_OF_TERM
    
    # Governance rules
    min_signatories: int = 3           # Bank requirement
    withdrawal_approval_count: int = 2  # Approvals needed for withdrawal
    quorum_percentage: float = 50.0     # % of members needed for votes
    
    # Term
    term_start: Optional[date] = None
    term_end: Optional[date] = None
    
    # Amendment
    amendment_approval_percentage: float = 75.0  # % needed to change constitution
    
    # Full text
    full_text: str = ""
    version: int = 1
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None


@dataclass
class Stokvel:
    """
    Core stokvel entity.
    
    Defined as: A group of natural persons with a common bond,
    joined together to form an invitation-only group savings scheme
    or rotating credit scheme that establishes a continuous pool
    of capital through member subscriptions.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    organization_id: str = ""          # Multi-tenancy
    
    # Identity
    name: str = ""
    slug: str = ""
    description: str = ""
    stokvel_type: str = "savings"      # From StokvelType enum in auth
    
    # Status
    status: StokvelStatus = StokvelStatus.DRAFT
    
    # Registration
    nasasa_registered: bool = False
    nasasa_registration_number: Optional[str] = None
    registration_date: Optional[date] = None
    
    # Financial
    total_pool: float = 0.0            # Current pool balance
    target_amount: Optional[float] = None
    currency: str = "ZAR"
    
    # Banks Act compliance
    # Stokvels < R100,000 exempt from registering with Stokvel Association
    banks_act_exempt: bool = True
    
    # Constitution
    constitution_id: Optional[str] = None
    
    # Metadata
    metadata: dict = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    @property
    def is_banks_act_exempt(self) -> bool:
        """Check if stokvel qualifies for Banks Act exemption."""
        return self.total_pool < 100_000  # R100,000 threshold
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "stokvel_type": self.stokvel_type,
            "status": self.status.value,
            "total_pool": self.total_pool,
            "currency": self.currency,
            "nasasa_registered": self.nasasa_registered,
            "banks_act_exempt": self.is_banks_act_exempt,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AuditLogEntry:
    """
    Audit log for all stokvel actions.
    
    SA stokvel governance principle: audit logs for everything.
    No single-admin control - all actions are recorded.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stokvel_id: str = ""
    organization_id: str = ""
    
    # Who
    user_id: str = ""
    user_role: str = ""
    
    # What
    action: str = ""          # e.g., "contribution_recorded", "member_invited"
    entity_type: str = ""     # e.g., "contribution", "member", "vote"
    entity_id: str = ""
    
    # Details
    description: str = ""
    metadata: dict = field(default_factory=dict)
    
    # When
    timestamp: datetime = field(default_factory=datetime.utcnow)
