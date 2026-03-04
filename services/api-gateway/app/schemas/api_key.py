from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ApiKeyBase(BaseModel):
    name: str

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKeyResponse(ApiKeyBase):
    id: UUID
    api_key: str
    api_secret: Optional[str] = None # Only populated on creation
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None

    class Config:
        from_attributes = True
