"""
Permissions & Access Control
=============================
Role-based permission system for stokvel governance.
Inspired by Saleor's permission system (AccountPermissions, OrderPermissions, etc.)

Key principle from SA stokvel law:
- NO single-admin control
- Voting required for spend
- Multiple signatories for bank operations (minimum 3)
- Audit trail for all financial actions
"""

from enum import Enum
from typing import Set, Optional
from .models import StokvelRole, StokvelMembership


class StokvelPermission(str, Enum):
    """
    Granular permissions for stokvel operations.
    Follows Saleor's pattern of enum-based permissions.
    """
    # Member management
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    VIEW_MEMBERS = "view_members"
    MANAGE_ROLES = "manage_roles"
    
    # Financial operations  
    VIEW_CONTRIBUTIONS = "view_contributions"
    RECORD_CONTRIBUTION = "record_contribution"
    APPROVE_WITHDRAWAL = "approve_withdrawal"
    VIEW_FINANCIAL_REPORTS = "view_financial_reports"
    MANAGE_BANK_ACCOUNT = "manage_bank_account"
    
    # Governance
    CREATE_VOTE = "create_vote"
    CAST_VOTE = "cast_vote"
    VIEW_VOTES = "view_votes"
    MANAGE_CONSTITUTION = "manage_constitution"
    
    # Stokvel management
    UPDATE_STOKVEL_SETTINGS = "update_stokvel_settings"
    VIEW_STOKVEL_DETAILS = "view_stokvel_details"
    MANAGE_DEALS = "manage_deals"
    
    # Admin
    VIEW_AUDIT_LOG = "view_audit_log"
    MANAGE_DISPUTES = "manage_disputes"
    FREEZE_ACCOUNT = "freeze_account"


# ──────────────────────────────────────────────
# Role -> Permission Mapping
# ──────────────────────────────────────────────

ROLE_PERMISSIONS: dict[StokvelRole, Set[StokvelPermission]] = {
    StokvelRole.CHAIRPERSON: {
        # Full governance powers
        StokvelPermission.INVITE_MEMBERS,
        StokvelPermission.REMOVE_MEMBERS,
        StokvelPermission.VIEW_MEMBERS,
        StokvelPermission.MANAGE_ROLES,
        StokvelPermission.VIEW_CONTRIBUTIONS,
        StokvelPermission.RECORD_CONTRIBUTION,
        StokvelPermission.APPROVE_WITHDRAWAL,
        StokvelPermission.VIEW_FINANCIAL_REPORTS,
        StokvelPermission.MANAGE_BANK_ACCOUNT,
        StokvelPermission.CREATE_VOTE,
        StokvelPermission.CAST_VOTE,
        StokvelPermission.VIEW_VOTES,
        StokvelPermission.MANAGE_CONSTITUTION,
        StokvelPermission.UPDATE_STOKVEL_SETTINGS,
        StokvelPermission.VIEW_STOKVEL_DETAILS,
        StokvelPermission.MANAGE_DEALS,
        StokvelPermission.VIEW_AUDIT_LOG,
        StokvelPermission.MANAGE_DISPUTES,
        StokvelPermission.FREEZE_ACCOUNT,
    },
    
    StokvelRole.SECRETARY: {
        StokvelPermission.INVITE_MEMBERS,
        StokvelPermission.VIEW_MEMBERS,
        StokvelPermission.VIEW_CONTRIBUTIONS,
        StokvelPermission.VIEW_FINANCIAL_REPORTS,
        StokvelPermission.CREATE_VOTE,
        StokvelPermission.CAST_VOTE,
        StokvelPermission.VIEW_VOTES,
        StokvelPermission.MANAGE_CONSTITUTION,
        StokvelPermission.VIEW_STOKVEL_DETAILS,
        StokvelPermission.VIEW_AUDIT_LOG,
    },
    
    StokvelRole.TREASURER: {
        StokvelPermission.VIEW_MEMBERS,
        StokvelPermission.VIEW_CONTRIBUTIONS,
        StokvelPermission.RECORD_CONTRIBUTION,
        StokvelPermission.APPROVE_WITHDRAWAL,
        StokvelPermission.VIEW_FINANCIAL_REPORTS,
        StokvelPermission.MANAGE_BANK_ACCOUNT,
        StokvelPermission.CAST_VOTE,
        StokvelPermission.VIEW_VOTES,
        StokvelPermission.VIEW_STOKVEL_DETAILS,
        StokvelPermission.VIEW_AUDIT_LOG,
    },
    
    StokvelRole.SIGNATORY: {
        StokvelPermission.VIEW_MEMBERS,
        StokvelPermission.VIEW_CONTRIBUTIONS,
        StokvelPermission.APPROVE_WITHDRAWAL,
        StokvelPermission.VIEW_FINANCIAL_REPORTS,
        StokvelPermission.CAST_VOTE,
        StokvelPermission.VIEW_VOTES,
        StokvelPermission.VIEW_STOKVEL_DETAILS,
    },
    
    StokvelRole.MEMBER: {
        StokvelPermission.VIEW_MEMBERS,
        StokvelPermission.VIEW_CONTRIBUTIONS,
        StokvelPermission.VIEW_FINANCIAL_REPORTS,
        StokvelPermission.CAST_VOTE,
        StokvelPermission.VIEW_VOTES,
        StokvelPermission.VIEW_STOKVEL_DETAILS,
    },
    
    StokvelRole.OBSERVER: {
        StokvelPermission.VIEW_STOKVEL_DETAILS,
        StokvelPermission.VIEW_VOTES,
    },
}


def has_permission(
    membership: StokvelMembership,
    permission: StokvelPermission,
) -> bool:
    """Check if a member has a specific permission."""
    if not membership.is_active:
        return False
    role_perms = ROLE_PERMISSIONS.get(membership.role, set())
    return permission in role_perms


def get_permissions(role: StokvelRole) -> Set[StokvelPermission]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())


def check_multi_signatory(
    memberships: list[StokvelMembership],
    required_signatories: int = 2,
) -> bool:
    """
    Verify that enough signatories have approved an action.
    
    SA stokvel governance principle:
    - No single person should control finances
    - Bank operations require minimum 3 signatories
    - Financial decisions need multiple approvals
    """
    active_signatories = [
        m for m in memberships 
        if m.is_signatory and m.is_active
    ]
    return len(active_signatories) >= required_signatories
