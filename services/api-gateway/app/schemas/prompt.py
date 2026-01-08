from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class SystemPromptBase(BaseModel):
    name: str
    description: Optional[str] = None
    template: str
    input_variables: List[str] = []
    is_active: bool = True

class SystemPromptCreate(SystemPromptBase):
    pass

class SystemPromptUpdate(BaseModel):
    description: Optional[str] = None
    template: Optional[str] = None
    input_variables: Optional[List[str]] = None
    is_active: Optional[bool] = None

class SystemPromptResponse(SystemPromptBase):
    id: UUID
    owner_id: UUID
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AuditLogCreate(BaseModel):
    user_id: UUID
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    changes: Optional[Dict[str, Any]] = None

class RenderPromptRequest(BaseModel):
    variables: Dict[str, Any]

class RenderPromptResponse(BaseModel):
    rendered_text: str
    missing_variables: List[str]
