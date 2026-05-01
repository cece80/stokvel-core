from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, constr
from typing import List, Optional
from app.api.v1.dependencies import get_current_user
from app.services import stokvel_service

router = APIRouter(prefix="/stokvels", tags=["stokvels"])

class StokvelCreateRequest(BaseModel):
    name: constr(min_length=1)
    stokvel_type: constr(min_length=1)
    description: Optional[str] = ""
    contribution_amount: float
    contribution_frequency: constr(min_length=1)
    payout_method: constr(min_length=1)
    target_amount: Optional[float] = None
    min_members: int = 3
    max_members: int = 50

class StokvelUpdateRequest(BaseModel):
    name: Optional[constr(min_length=1)] = None
    description: Optional[str] = None
    contribution_amount: Optional[float] = None
    contribution_frequency: Optional[constr(min_length=1)] = None
    payout_method: Optional[constr(min_length=1)] = None
    target_amount: Optional[float] = None
    min_members: Optional[int] = None
    max_members: Optional[int] = None

@router.post("/create")
async def create_stokvel(data: StokvelCreateRequest, user=Depends(get_current_user)):
    stokvel = await stokvel_service.create_stokvel(user, data)
    return stokvel

@router.get("")
async def list_stokvels(user=Depends(get_current_user)):
    stokvels = await stokvel_service.list_stokvels(user)
    return stokvels

@router.get("/{stokvel_id}")
async def get_stokvel(stokvel_id: str, user=Depends(get_current_user)):
    stokvel = await stokvel_service.get_stokvel(user, stokvel_id)
    return stokvel

@router.put("/{stokvel_id}")
async def update_stokvel(stokvel_id: str, data: StokvelUpdateRequest, user=Depends(get_current_user)):
    stokvel = await stokvel_service.update_stokvel(user, stokvel_id, data)
    return stokvel

@router.delete("/{stokvel_id}")
async def delete_stokvel(stokvel_id: str, user=Depends(get_current_user)):
    await stokvel_service.delete_stokvel(user, stokvel_id)
    return {"success": True}
