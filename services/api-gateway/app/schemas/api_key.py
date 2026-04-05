from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class ApiKeyBase(BaseModel):
    name: str
    fund_id: Optional[UUID] = None
    role: str = "VIEWER"
    scopes: List[str] = ["*"]
    allowed_ips: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    rate_limit_rpm: int = 60

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    allowed_ips: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    rate_limit_rpm: Optional[int] = None

class ApiKeyResponse(ApiKeyBase):
    id: UUID
    api_key: str
    api_secret: Optional[str] = None  # Only populated on creation
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
