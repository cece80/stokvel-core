"""
Stokvel Governance
====================
Officer management, voting, and dispute resolution.

SA Stokvel Governance Principles:
- No single-admin control
- Voting required for financial decisions
- Multiple signatories for bank operations
- Complete audit trail
- Democratic decision-making
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
import uuid

from auth.models import StokvelMembership, StokvelRole
from auth.permissions import StokvelPermission, has_permission
from .models import Stokvel, StokvelConstitution, AuditLogEntry


@dataclass
class Vote:
    """A governance vote/proposal."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stokvel_id: str = ""
    
    # Proposal
    title: str = ""
    description: str = ""
    proposal_type: str = "general"  # general, financial, constitutional, member_removal
    
    # Creator
    created_by: str = ""
    
    # Voting
    votes_for: int = 0
    votes_against: int = 0
    votes_abstain: int = 0
    total_eligible_voters: int = 0
    quorum_percentage: float = 50.0
    approval_percentage: float = 50.0  # Simple majority default
    
    # Status
    is_open: bool = True
    result: Optional[str] = None  # approved, rejected, no_quorum
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    closes_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


@dataclass
class VoteCast:
    """Individual vote record."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vote_id: str = ""
    user_id: str = ""
    choice: str = "for"  # for, against, abstain
    cast_at: datetime = field(default_factory=datetime.utcnow)


def create_vote(
    stokvel: Stokvel,
    creator_membership: StokvelMembership,
    title: str,
    description: str,
    proposal_type: str = "general",
    total_eligible_voters: int = 0,
    quorum_percentage: float = 50.0,
    approval_percentage: float = 50.0,
) -> dict:
    """Create a new governance vote."""
    if not has_permission(creator_membership, StokvelPermission.CREATE_VOTE):
        return {"success": False, "error": "No permission to create votes"}
    
    # Constitutional amendments need 75% approval
    if proposal_type == "constitutional":
        approval_percentage = 75.0
    
    vote = Vote(
        stokvel_id=stokvel.id,
        title=title,
        description=description,
        proposal_type=proposal_type,
        created_by=creator_membership.user_id,
        total_eligible_voters=total_eligible_voters,
        quorum_percentage=quorum_percentage,
        approval_percentage=approval_percentage,
    )
    
    return {
        "success": True,
        "vote_id": vote.id,
        "title": title,
        "message": f"Vote created: {title}",
    }


def cast_vote(
    vote: Vote,
    membership: StokvelMembership,
    choice: str,
    existing_votes: List[VoteCast],
) -> dict:
    """Cast a vote on a proposal."""
    if not vote.is_open:
        return {"success": False, "error": "Voting is closed"}
    
    if not has_permission(membership, StokvelPermission.CAST_VOTE):
        return {"success": False, "error": "No permission to vote"}
    
    # Check if already voted
    already_voted = any(v.user_id == membership.user_id for v in existing_votes)
    if already_voted:
        return {"success": False, "error": "You have already voted"}
    
    # Record vote
    vote_cast = VoteCast(
        vote_id=vote.id,
        user_id=membership.user_id,
        choice=choice,
    )
    
    # Update tallies
    if choice == "for":
        vote.votes_for += 1
    elif choice == "against":
        vote.votes_against += 1
    else:
        vote.votes_abstain += 1
    
    return {
        "success": True,
        "vote_id": vote.id,
        "choice": choice,
        "current_tally": {
            "for": vote.votes_for,
            "against": vote.votes_against,
            "abstain": vote.votes_abstain,
        },
    }


def close_vote(vote: Vote) -> dict:
    """Close voting and determine result."""
    vote.is_open = False
    vote.closed_at = datetime.utcnow()
    
    total_cast = vote.votes_for + vote.votes_against + vote.votes_abstain
    
    # Check quorum
    if vote.total_eligible_voters > 0:
        participation = (total_cast / vote.total_eligible_voters) * 100
        if participation < vote.quorum_percentage:
            vote.result = "no_quorum"
            return {
                "success": True,
                "result": "no_quorum",
                "message": f"Vote failed: quorum not reached ({participation:.1f}% vs {vote.quorum_percentage}% required)",
            }
    
    # Check approval
    voting_total = vote.votes_for + vote.votes_against  # Abstentions don't count
    if voting_total > 0:
        approval = (vote.votes_for / voting_total) * 100
        if approval >= vote.approval_percentage:
            vote.result = "approved"
        else:
            vote.result = "rejected"
    else:
        vote.result = "no_votes"
    
    return {
        "success": True,
        "result": vote.result,
        "tally": {
            "for": vote.votes_for,
            "against": vote.votes_against,
            "abstain": vote.votes_abstain,
        },
        "message": f"Vote result: {vote.result}",
    }


def log_audit_event(
    stokvel_id: str,
    organization_id: str,
    user_id: str,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    description: str = "",
    metadata: dict = None,
) -> AuditLogEntry:
    """
    Create an audit log entry.
    
    Every significant action in the stokvel is logged for transparency.
    This is a core governance requirement - no single-admin control.
    """
    return AuditLogEntry(
        stokvel_id=stokvel_id,
        organization_id=organization_id,
        user_id=user_id,
        user_role=user_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        metadata=metadata or {},
    )
