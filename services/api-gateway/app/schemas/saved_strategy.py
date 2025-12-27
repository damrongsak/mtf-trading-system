from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SavedStrategyBase(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    code: str
    parameters: Optional[Dict[str, Any]] = {}
    last_results: Optional[Dict[str, Any]] = None
    last_optimization_result: Optional[List[Dict[str, Any]]] = None
    last_simulation_result: Optional[Dict[str, Any]] = None
    is_public: bool = False

class SavedStrategyCreate(SavedStrategyBase):
    pass

class SavedStrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    last_results: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None

class SavedStrategyResponse(SavedStrategyBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
