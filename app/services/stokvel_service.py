from decimal import Decimal
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.stokvel import (
    Stokvel, StokvelConstitution, StokvelStatus, Contribution, Vote, VoteCast, AuditLogEntry, PayoutMethod, ContributionFrequency
)
from app.models.user import StokvelRole, StokvelMembership, User
from app.core.redis import cache_set, cache_get

# TODO: Replace with DB
_STOKVELS: Dict[str, Stokvel] = {}

class StokvelService:
    @staticmethod
    async def create_stokvel(
        creator: User,
        data,
    ) -> Dict[str, Any]:
        stokvel = Stokvel(
            organization_id=creator.default_organization_id or "",
            name=data.name,
            slug=data.name.lower().replace(" ", "-"),
            description=data.description or "",
            stokvel_type=data.stokvel_type,
            status=StokvelStatus.DRAFT,
            target_amount=data.target_amount,
            created_by=creator.id,
        )
        constitution = StokvelConstitution(
            stokvel_id=stokvel.id,
            min_members=data.min_members,
            max_members=data.max_members,
            contribution_amount=Decimal(str(data.contribution_amount)),
            contribution_frequency=ContributionFrequency(data.contribution_frequency),
            payout_method=PayoutMethod(data.payout_method),
        )
        stokvel.constitution_id = constitution.id
        membership = StokvelMembership(
            user_id=creator.id,
            stokvel_id=stokvel.id,
            organization_id=stokvel.organization_id,
            role=StokvelRole.CHAIRPERSON,
            is_signatory=True,
            contribution_amount=float(data.contribution_amount),
        )
        _STOKVELS[stokvel.id] = stokvel
        await cache_set(f"stokvel:{stokvel.id}", stokvel.__dict__, 3600)
        return {
            "stokvel": stokvel.__dict__,
            "constitution": constitution.__dict__,
            "membership": membership.__dict__,
        }

    @staticmethod
    async def list_stokvels(user: User, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        # TODO: Replace with DB query
        items = [s.__dict__ for s in _STOKVELS.values() if s.organization_id == (user.default_organization_id or "")]
        total_count = len(items)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "items": items[start:end],
            "total_count": total_count,
            "page": page,
            "per_page": per_page,
        }

    @staticmethod
    async def get_stokvel(user: User, stokvel_id: str) -> Dict[str, Any]:
        stokvel = _STOKVELS.get(stokvel_id)
        if not stokvel:
            raise Exception("Stokvel not found")
        return stokvel.__dict__

    @staticmethod
    async def update_stokvel(user: User, stokvel_id: str, data) -> Dict[str, Any]:
        stokvel = _STOKVELS.get(stokvel_id)
        if not stokvel:
            raise Exception("Stokvel not found")
        for k, v in data.dict(exclude_unset=True).items():
            setattr(stokvel, k, v)
        stokvel.updated_at = datetime.utcnow()
        await cache_set(f"stokvel:{stokvel.id}", stokvel.__dict__, 3600)
        return stokvel.__dict__

    @staticmethod
    async def delete_stokvel(user: User, stokvel_id: str) -> None:
        if stokvel_id in _STOKVELS:
            del _STOKVELS[stokvel_id]
        # TODO: Remove from cache
