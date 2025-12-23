from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, UUID4, ConfigDict
from app.database import get_db
from app.models.strategy import Strategy
from app.models.user_fund import Fund, User, UserFund
from app.routers.auth import oauth2_scheme
from app.security import get_current_user
from app.schemas.response import APIResponse, PaginatedResponse
from app.utils.response import success_response, paginated_response

router = APIRouter(
    prefix="/api/v1/strategies",
    tags=["strategies"]
)

class StrategyCreate(BaseModel):
    name: str
    fund_id: UUID4
    template_id: str
    broker_account_id: UUID4
    config_json: dict
    risk_settings: dict = {}

class StrategyResponse(BaseModel):
    id: UUID4
    name: str
    template_id: str
    broker_account_id: Optional[UUID4]
    config_json: dict
    risk_settings: dict
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

@router.post("/", response_model=APIResponse[StrategyResponse])
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # Verify fund exists
    fund = db.query(Fund).filter(Fund.id == strategy.fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
    
    new_strategy = Strategy(
        name=strategy.name,
        fund_id=strategy.fund_id,
        template_id=strategy.template_id,
        broker_account_id=strategy.broker_account_id,
        config_json=strategy.config_json,
        risk_settings=strategy.risk_settings
    )
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    return success_response(data=StrategyResponse.model_validate(new_strategy))

@router.get("/", response_model=PaginatedResponse[StrategyResponse])
def list_strategies(
    fund_id: Optional[UUID4] = None, 
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if fund_id:
        # Check access
        # Assuming we check if user belongs to fund
        # For now, simplistic check or trust if valid
        query = db.query(Strategy).filter(Strategy.fund_id == fund_id)
    else:
        # Join strategies -> funds -> user_funds to get all strategies for this user
        query = db.query(Strategy).join(Fund).join(UserFund).filter(UserFund.user_id == current_user.id)
        
    total = query.count()
    strategies = query.offset((page - 1) * per_page).limit(per_page).all()
    
    return paginated_response(
        data=[StrategyResponse.model_validate(s) for s in strategies],
        page=page,
        per_page=per_page,
        total=total
    )

class StrategyConfigUpdate(BaseModel):
    config_json: Optional[dict] = None
    risk_settings: Optional[dict] = None
    is_active: Optional[bool] = None

@router.post("/{id}/config", response_model=APIResponse[StrategyResponse])
def update_strategy_config(id: UUID4, config: StrategyConfigUpdate, db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    strategy = db.query(Strategy).filter(Strategy.id == id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    if config.config_json is not None:
        strategy.config_json = config.config_json
    if config.risk_settings is not None:
        strategy.risk_settings = config.risk_settings
    if config.is_active is not None:
        strategy.is_active = config.is_active
        
    db.commit()
    db.refresh(strategy)
    
    # TODO: Publish to Redis here
    
    return success_response(data=StrategyResponse.model_validate(strategy))

class LogicTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    default_config: dict
    default_risk_settings: dict

@router.get("/templates", response_model=APIResponse[List[LogicTemplateResponse]])
def list_templates():
    # Mock data for now - typically fetching from Strategy Core Registry
    templates = [
        LogicTemplateResponse(
            id="SMC_V1",
            name="Smart Money Concepts V1",
            description="Order Block + FVG strategy with MTF analysis",
            default_config={
                "timeframes": ["15m", "1h", "4h"],
                "risk_per_trade": 1.0,
                "rr_ratio": 2.0
            },
            default_risk_settings={
                "max_drawdown": 5.0,
                "daily_loss_limit": 2.0
            }
        ),
        LogicTemplateResponse(
            id="MACD_CROSS_V1",
            name="MACD Crossover",
            description="Classic MACD crossover strategy",
            default_config={
                "fast": 12,
                "slow": 26,
                "signal": 9
            },
            default_risk_settings={
                 "max_drawdown": 10.0
            }
        )
    ]
    return success_response(data=templates)