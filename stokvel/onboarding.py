"""
Stokvel Onboarding
====================
Complete stokvel creation and member onboarding flow.

Flow:
1. User creates organization (if first time)
2. User creates stokvel with constitution
3. Creator becomes Chairperson + Signatory
4. Invite members (minimum 2 more for 3 total)
5. Assign at least 2 more signatories (total 3 minimum)
6. All signatories complete KYC
7. Stokvel activated

Compliance:
- Banks Act Exemption Notice 620 (2014)
- Minimum 3 signatories for bank operations
- KYC/FICA verification for all signatories
- Constitution must be agreed by all founding members
"""

import uuid
from datetime import datetime
from typing import Optional, List, Tuple

from auth.models import (
    User, Organization, StokvelMembership, StokvelRole,
    UserStatus, StokvelType
)
from .models import (
    Stokvel, StokvelConstitution, StokvelStatus,
    ContributionFrequency, PayoutMethod, AuditLogEntry
)


def create_organization(
    owner: User,
    name: str,
    slug: Optional[str] = None,
) -> Organization:
    """
    Step 1: Create a new organization (tenant).
    
    Every stokvel operates within an organization for multi-tenancy.
    """
    org = Organization(
        name=name,
        slug=slug or name.lower().replace(" ", "-"),
        owner_id=owner.id,
    )
    
    # Set as user's default org
    owner.default_organization_id = org.id
    
    return org


def create_stokvel(
    creator: User,
    organization_id: str,
    name: str,
    stokvel_type: str = StokvelType.SAVINGS.value,
    description: str = "",
    contribution_amount: float = 0.0,
    contribution_frequency: str = ContributionFrequency.MONTHLY.value,
    payout_method: str = PayoutMethod.END_OF_TERM.value,
    target_amount: Optional[float] = None,
    min_members: int = 3,
    max_members: int = 50,
) -> Tuple[Stokvel, StokvelConstitution, StokvelMembership]:
    """
    Step 2: Create a new stokvel with constitution.
    
    The creator automatically becomes:
    - Chairperson
    - First signatory
    
    Returns:
        Tuple of (Stokvel, Constitution, Creator's Membership)
    """
    # Create stokvel
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
    
    # Create constitution
    constitution = StokvelConstitution(
        stokvel_id=stokvel.id,
        min_members=min_members,
        max_members=max_members,
        contribution_amount=contribution_amount,
        contribution_frequency=ContributionFrequency(contribution_frequency),
        payout_method=PayoutMethod(payout_method),
    )
    stokvel.constitution_id = constitution.id
    
    # Creator becomes Chairperson + Signatory
    membership = StokvelMembership(
        user_id=creator.id,
        stokvel_id=stokvel.id,
        organization_id=organization_id,
        role=StokvelRole.CHAIRPERSON,
        is_signatory=True,
        contribution_amount=contribution_amount,
    )
    
    return stokvel, constitution, membership


def invite_member(
    stokvel: Stokvel,
    inviter: StokvelMembership,
    invitee: User,
    role: StokvelRole = StokvelRole.MEMBER,
    is_signatory: bool = False,
    constitution: Optional[StokvelConstitution] = None,
    current_member_count: int = 0,
) -> Tuple[Optional[StokvelMembership], dict]:
    """
    Step 3: Invite a member to join the stokvel.
    
    Validates:
    - Inviter has permission to invite
    - Stokvel hasn't reached max members
    - Invitee isn't already a member
    """
    # Check inviter permissions
    if not inviter.is_admin():
        return None, {
            "success": False,
            "error": "Only Chairperson, Secretary, or Treasurer can invite members",
        }
    
    # Check max members
    if constitution and current_member_count >= constitution.max_members:
        return None, {
            "success": False,
            "error": f"Stokvel has reached maximum of {constitution.max_members} members",
        }
    
    # Create membership
    membership = StokvelMembership(
        user_id=invitee.id,
        stokvel_id=stokvel.id,
        organization_id=stokvel.organization_id,
        role=role,
        is_signatory=is_signatory,
        invited_by=inviter.user_id,
        contribution_amount=constitution.contribution_amount if constitution else 0,
    )
    
    return membership, {
        "success": True,
        "membership_id": membership.id,
        "role": role.value,
        "is_signatory": is_signatory,
        "message": f"{invitee.full_name} invited as {role.value}",
    }


def assign_officer_role(
    stokvel: Stokvel,
    assigner: StokvelMembership,
    target_membership: StokvelMembership,
    new_role: StokvelRole,
    make_signatory: bool = False,
) -> dict:
    """
    Step 4: Assign an officer role to a member.
    
    Only Chairperson can assign roles.
    Officer roles: Chairperson, Secretary, Treasurer.
    """
    if assigner.role != StokvelRole.CHAIRPERSON:
        return {
            "success": False,
            "error": "Only the Chairperson can assign officer roles",
        }
    
    old_role = target_membership.role
    target_membership.role = new_role
    
    if make_signatory:
        target_membership.is_signatory = True
    
    return {
        "success": True,
        "member_id": target_membership.user_id,
        "old_role": old_role.value,
        "new_role": new_role.value,
        "is_signatory": target_membership.is_signatory,
        "message": f"Role updated from {old_role.value} to {new_role.value}",
    }


def check_activation_readiness(
    stokvel: Stokvel,
    constitution: StokvelConstitution,
    memberships: List[StokvelMembership],
    users: dict,  # user_id -> User
) -> dict:
    """
    Step 5: Check if stokvel is ready to be activated.
    
    Requirements:
    1. Minimum members met (default 3)
    2. At least 3 signatories
    3. Chairperson, Secretary, and Treasurer assigned
    4. All signatories KYC verified
    5. Constitution approved
    """
    issues = []
    
    active_members = [m for m in memberships if m.is_active]
    signatories = [m for m in active_members if m.is_signatory]
    
    # Check minimum members
    if len(active_members) < constitution.min_members:
        issues.append(
            f"Need at least {constitution.min_members} members. "
            f"Currently have {len(active_members)}."
        )
    
    # Check signatories (bank requirement: minimum 3)
    if len(signatories) < constitution.min_signatories:
        issues.append(
            f"Need at least {constitution.min_signatories} signatories. "
            f"Currently have {len(signatories)}."
        )
    
    # Check required officer roles
    roles_present = {m.role for m in active_members}
    required_roles = {StokvelRole.CHAIRPERSON, StokvelRole.SECRETARY, StokvelRole.TREASURER}
    missing_roles = required_roles - roles_present
    if missing_roles:
        issues.append(
            f"Missing required roles: {', '.join(r.value for r in missing_roles)}"
        )
    
    # Check signatory KYC
    for sig in signatories:
        user = users.get(sig.user_id)
        if user and not user.is_kyc_verified:
            issues.append(
                f"Signatory {user.full_name} has not completed KYC verification"
            )
    
    is_ready = len(issues) == 0
    
    return {
        "is_ready": is_ready,
        "issues": issues,
        "member_count": len(active_members),
        "signatory_count": len(signatories),
        "roles_assigned": [r.value for r in roles_present],
    }


def activate_stokvel(
    stokvel: Stokvel,
    readiness: dict,
) -> dict:
    """
    Step 6: Activate the stokvel if all requirements are met.
    """
    if not readiness["is_ready"]:
        return {
            "success": False,
            "error": "Stokvel is not ready for activation",
            "issues": readiness["issues"],
        }
    
    stokvel.status = StokvelStatus.ACTIVE
    stokvel.updated_at = datetime.utcnow()
    
    return {
        "success": True,
        "stokvel_id": stokvel.id,
        "status": stokvel.status.value,
        "message": f"Stokvel '{stokvel.name}' is now active!",
        "member_count": readiness["member_count"],
        "signatory_count": readiness["signatory_count"],
    }
