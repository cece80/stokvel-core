
from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models import (
    Stokvel, StokvelConstitution, StokvelMembership, StokvelRole, StokvelStatus,
    Contribution, Vote, VoteCast, AuditLogEntry, User
)

class StokvelService:
    @staticmethod
    def create_stokvel(
        creator: User,
        organization_id: str,
        name: str,
        stokvel_type: str,
        description: str = "",
        contribution_amount: Decimal = Decimal("0.0"),
        contribution_frequency: str = "monthly",
        payout_method: str = "end_of_term",
        target_amount: Optional[Decimal] = None,
        min_members: int = 3,
        max_members: int = 50,
    ) -> Dict[str, Any]:
        stokvel = Stokvel(
            organization_id=organization_id,
            name=name,
            slug=name.lower().replace(" ", "-"),
            description=description,
            stokvel_type=stokvel_type,
            status=StokvelStatus.DRAFT,
            target_amount=target_amount,
            created_by=creator.id,
        )
        constitution = StokvelConstitution(
            stokvel_id=stokvel.id,
            min_members=min_members,
            max_members=max_members,
            contribution_amount=contribution_amount,
            contribution_frequency=contribution_frequency,
            payout_method=payout_method,
        )
        stokvel.constitution_id = constitution.id
        membership = StokvelMembership(
            user_id=creator.id,
            stokvel_id=stokvel.id,
            organization_id=organization_id,
            role=StokvelRole.CHAIRPERSON,
            is_signatory=True,
            contribution_amount=contribution_amount,
        )
        # Save to DB (stub)
        return {
            "stokvel": stokvel,
            "constitution": constitution,
            "membership": membership,
        }

    @staticmethod
    def get_stokvel(stokvel_id: str) -> Optional[Stokvel]:
        # Stub: fetch from DB
        return Stokvel.get_by_id(stokvel_id)

    @staticmethod
    def update_stokvel(stokvel_id: str, updates: Dict[str, Any]) -> Optional[Stokvel]:
        stokvel = Stokvel.get_by_id(stokvel_id)
        if not stokvel:
            return None
        for k, v in updates.items():
            setattr(stokvel, k, v)
        stokvel.updated_at = datetime.utcnow()
        stokvel.save()
        return stokvel

    @staticmethod
    def add_member(
        stokvel: Stokvel,
        inviter: StokvelMembership,
        invitee: User,
        role: StokvelRole = StokvelRole.MEMBER,
        is_signatory: bool = False,
        constitution: Optional[StokvelConstitution] = None,
        current_member_count: int = 0,
    ) -> Dict[str, Any]:
        if not inviter.is_admin():
            return {"success": False, "error": "Only officers can invite members."}
        if constitution and current_member_count >= constitution.max_members:
            return {"success": False, "error": f"Stokvel has reached maximum of {constitution.max_members} members"}
        membership = StokvelMembership(
            user_id=invitee.id,
            stokvel_id=stokvel.id,
            organization_id=stokvel.organization_id,
            role=role,
            is_signatory=is_signatory,
            invited_by=inviter.user_id,
            contribution_amount=constitution.contribution_amount if constitution else Decimal("0.0"),
        )
        # Save to DB (stub)
        return {"success": True, "membership": membership}

    @staticmethod
    def remove_member(stokvel: Stokvel, membership: StokvelMembership) -> Dict[str, Any]:
        membership.is_active = False
        membership.removed_at = datetime.utcnow()
        membership.save()
        return {"success": True, "message": "Member removed."}

    @staticmethod
    def record_contribution(stokvel: Stokvel, member: StokvelMembership, amount: Decimal) -> Dict[str, Any]:
        contribution = Contribution(
            stokvel_id=stokvel.id,
            user_id=member.user_id,
            amount=amount,
            contributed_at=datetime.utcnow(),
        )
        # Save to DB (stub)
        return {"success": True, "contribution": contribution}

    # Governance voting logic
    @staticmethod
    def create_vote(
        stokvel: Stokvel,
        creator_membership: StokvelMembership,
        title: str,
        description: str,
        proposal_type: str = "general",
        total_eligible_voters: int = 0,
        quorum_percentage: float = 50.0,
        approval_percentage: float = 50.0,
    ) -> Dict[str, Any]:
        if not creator_membership.can_create_vote():
            return {"success": False, "error": "No permission to create votes"}
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
        # Save to DB (stub)
        return {"success": True, "vote_id": vote.id, "title": title, "message": f"Vote created: {title}"}

    @staticmethod
    def cast_vote(
        vote: Vote,
        membership: StokvelMembership,
        choice: str,
        existing_votes: List[VoteCast],
    ) -> Dict[str, Any]:
        if not vote.is_open:
            return {"success": False, "error": "Voting is closed"}
        if not membership.can_cast_vote():
            return {"success": False, "error": "No permission to vote"}
        already_voted = any(v.user_id == membership.user_id for v in existing_votes)
        if already_voted:
            return {"success": False, "error": "You have already voted"}
        vote_cast = VoteCast(
            vote_id=vote.id,
            user_id=membership.user_id,
            choice=choice,
        )
        if choice == "for":
            vote.votes_for += 1
        elif choice == "against":
            vote.votes_against += 1
        else:
            vote.votes_abstain += 1
        # Save to DB (stub)
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

    @staticmethod
    def close_vote(vote: Vote) -> Dict[str, Any]:
        vote.is_open = False
        vote.closed_at = datetime.utcnow()
        total_cast = vote.votes_for + vote.votes_against + vote.votes_abstain
        if vote.total_eligible_voters > 0:
            participation = (total_cast / vote.total_eligible_voters) * 100
            if participation < vote.quorum_percentage:
                vote.result = "no_quorum"
                return {
                    "success": True,
                    "result": "no_quorum",
                    "message": f"Vote failed: quorum not reached ({participation:.1f}% vs {vote.quorum_percentage}% required)",
                }
        voting_total = vote.votes_for + vote.votes_against
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

    @staticmethod
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
        entry = AuditLogEntry(
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
        # Save to DB (stub)
        return entry
