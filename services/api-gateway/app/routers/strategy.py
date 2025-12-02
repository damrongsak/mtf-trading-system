from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, UUID4
from app.database import get_db
from app.models.strategy import Strategy
from app.models.user_fund import Fund
from app.routers.auth import oauth2_scheme
from app.schemas.response import APIResponse, PaginatedResponse
from app.utils.response import success_response, paginated_response

router = APIRouter(
    prefix="/api/v1/strategies",
    tags=["strategies"]
)

class StrategyCreate(BaseModel):
    name: str
    fund_id: UUID4
    type: str
    config_json: dict

class StrategyResponse(BaseModel):
    id: UUID4
    name: str
    type: str
    config_json: dict
    is_active: bool

    class Config:
        orm_mode = True

@router.post("/", response_model=APIResponse[StrategyResponse])
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # Verify fund exists
    fund = db.query(Fund).filter(Fund.id == strategy.fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    new_strategy = Strategy(
        name=strategy.name,
        fund_id=strategy.fund_id,
        type=strategy.type,
        config_json=strategy.config_json
    )
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    return success_response(data=new_strategy)

@router.get("/", response_model=PaginatedResponse[StrategyResponse])
def list_strategies(
    fund_id: UUID4, 
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    query = db.query(Strategy).filter(Strategy.fund_id == fund_id)
    total = query.count()
    strategies = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return paginated_response(
        data=strategies,
        page=page,
        per_page=per_page,
        total=total
    )
