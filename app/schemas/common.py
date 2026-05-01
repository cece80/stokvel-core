from pydantic import BaseModel
from typing import List, Optional, Any

class PaginatedResponse(BaseModel):
    items: List[Any]
    total_count: int
    page: int = 1
    per_page: int = 50

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None

class SuccessResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None
