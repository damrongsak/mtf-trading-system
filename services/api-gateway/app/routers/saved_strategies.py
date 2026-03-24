from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID

from app.database import get_db
from app.models.saved_strategy import SavedStrategy
from app.schemas.saved_strategy import SavedStrategyCreate, SavedStrategyUpdate, SavedStrategyResponse
from app.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/strategies/saved", tags=["Strategies (Library)"])

@router.post("/", response_model=SavedStrategyResponse)
def create_strategy(
    strategy: SavedStrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save a new custom strategy definition."""
    db_strategy = SavedStrategy(
        **strategy.model_dump(),
        user_id=current_user.id
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@router.get("/", response_model=List[SavedStrategyResponse])
def list_strategies(
    public_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List strategies.
    By default returns:
    1. Strategies owned by current user
    2. Strategies marked as public (from anyone)
    """
    query = db.query(SavedStrategy)
    
    if public_only:
        query = query.filter(SavedStrategy.is_public == True)
    else:
        # Show mine OR public
        query = query.filter(
            or_(
                SavedStrategy.user_id == current_user.id,
                SavedStrategy.is_public == True
            )
        )
    
    return query.order_by(SavedStrategy.updated_at.desc()).all()

@router.get("/{strategy_id}", response_model=SavedStrategyResponse)
def get_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific strategy. Checks ownership or visibility."""
    strategy = db.query(SavedStrategy).filter(SavedStrategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Check access
    if not strategy.is_public and strategy.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this strategy")
    
    return strategy

@router.put("/{strategy_id}", response_model=SavedStrategyResponse)
def update_strategy(
    strategy_id: UUID,
    update_data: SavedStrategyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a strategy. Only owner can update."""
    strategy = db.query(SavedStrategy).filter(SavedStrategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this strategy")
    
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(strategy, key, value)
    
    db.commit()
    db.refresh(strategy)
    return strategy

@router.delete("/{strategy_id}")
def delete_strategy(
    strategy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a strategy. Only owner can delete."""
    strategy = db.query(SavedStrategy).filter(SavedStrategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if strategy.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this strategy")
    
    db.delete(strategy)
    db.commit()
    return {"message": "Strategy deleted successfully"}
