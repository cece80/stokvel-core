from pydantic import BaseModel, Field, condecimal, constr
from typing import Optional, List
from decimal import Decimal

class CreateStokvelInput(BaseModel):
    name: str
    stokvel_type: str = "savings"
    description: Optional[str] = ""
    contribution_amount: condecimal(ge=0) = Decimal("0.00")
    contribution_frequency: str = "monthly"
    payout_method: str = "end_of_term"
    target_amount: Optional[condecimal(ge=0)] = None
    min_members: int = 3
    max_members: int = 50

class InviteMemberInput(BaseModel):
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str = "member"
    is_signatory: bool = False

class AssignRoleInput(BaseModel):
    role: str
    is_signatory: bool = False

class StokvelResponse(BaseModel):
    id: str
    name: str
    stokvel_type: str
    status: str
    member_count: int
    total_pool: condecimal(ge=0) = Decimal("0.00")
    currency: str = "ZAR"
    your_role: str
    is_signatory: bool = False
    created_at: str

class SubmitKYCInput(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    document_url: Optional[str] = None
    document_date: Optional[str] = None

class KYCStatusResponse(BaseModel):
    kyc_status: str
    has_id_document: bool = False
    has_proof_of_address: bool = False
    missing_documents: List[str] = []
    is_complete: bool = False

class AuditLogResponse(BaseModel):
    entries: List[dict] = []
    total_count: int = 0
    page: int = 1
    per_page: int = 50
