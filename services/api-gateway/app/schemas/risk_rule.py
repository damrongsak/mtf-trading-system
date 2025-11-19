"""
RiskRule Pydantic schemas for API request/response validation.
Source of truth: specs/01_data_model.yaml -> RiskRule entity
"""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from enum import Enum


class RuleType(str, Enum):
    """Category of risk rule."""
    RISK_CAP = "RISK_CAP"
    LOT_SIZE = "LOT_SIZE"
    VOLATILITY = "VOLATILITY"
    RR_RATIO = "RR_RATIO"


class RiskRuleBase(BaseModel):
    """Base risk rule schema."""
    rule_name: str = Field(..., max_length=100, description="Unique rule name")
    rule_type: RuleType = Field(..., description="Category of risk rule")
    threshold_value: Decimal = Field(..., description="Threshold value", decimal_places=2)
    threshold_unit: str = Field(..., max_length=20, description="Unit of measurement")
    is_active: bool = Field(True, description="Whether rule is enforced")
    description: Optional[str] = Field(None, description="Human-readable description")


class RiskRuleCreate(RiskRuleBase):
    """Schema for creating a new risk rule."""
    pass


class RiskRuleUpdate(BaseModel):
    """Schema for updating a risk rule."""
    threshold_value: Optional[Decimal] = Field(None, decimal_places=2)
    is_active: Optional[bool] = None
    description: Optional[str] = None


class RiskRuleResponse(RiskRuleBase):
    """Schema for risk rule API responses."""
    rule_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
