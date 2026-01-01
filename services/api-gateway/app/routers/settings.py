from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_preferences import UserPreferences, StrategyType
from app.security import get_current_user
from pydantic import BaseModel, ConfigDict
from app.schemas.response import APIResponse
from app.utils.response import success_response
import uuid

router = APIRouter(
    prefix="/api/v1/settings",
    tags=["settings"]
)


class UserPreferencesResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    default_fund_id: uuid.UUID | None = None
    
    
    # Trading Preferences
    preferred_timeframes: List[str]
    default_symbol: str
    session_preferences: List[str] | None = None
    
    model_config = ConfigDict(from_attributes=True)


class UpdatePreferencesDto(BaseModel):
    default_fund_id: uuid.UUID | None = None
    preferred_timeframes: List[str] | None = None
    default_symbol: str | None = None
    session_preferences: List[str] | None = None


@router.get("/preferences", response_model=APIResponse[UserPreferencesResponse])
async def get_preferences(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's preferences. Creates default preferences if none exist.
    """
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    # Create default preferences if none exist
    if not preferences:
        preferences = UserPreferences(
            user_id=current_user.id,
            preferred_timeframes=["4H", "1H", "15m"],
            default_symbol="XAU/USD"
        )
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    
    return success_response(
        data=UserPreferencesResponse.model_validate(preferences),
        message="User preferences retrieved successfully"
    )


@router.put("/preferences", response_model=APIResponse[UserPreferencesResponse])
async def update_preferences(
    data: UpdatePreferencesDto,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user preferences
    """
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).first()
    
    # Create if doesn't exist
    if not preferences:
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
    
    # Update preferences
    update_data = data.model_dump(exclude_unset=True)
    
    # Apply updates only for fields that are actually provided (not None or explicitly set)
    for field, value in update_data.items():
        # Skip None values to avoid overwriting defaults
        if value is not None:
            setattr(preferences, field, value)
    
    db.commit()
    db.refresh(preferences)
    
    return success_response(
        data=UserPreferencesResponse.model_validate(preferences),
        message="User preferences updated successfully"
    )
