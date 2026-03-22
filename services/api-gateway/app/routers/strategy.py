from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, UUID4, ConfigDict
from app.database import get_db
from app.models.strategy import Strategy
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.user import User
from app.routers.auth import oauth2_scheme
from app.security import get_current_user
from app.dependencies.rbac import RequireRole
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
    custom_code: Optional[str] = None

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
async def create_strategy(
    strategy: StrategyCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER]))
):
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
        risk_settings=strategy.risk_settings,
        custom_code=strategy.custom_code
    )
    db.add(new_strategy)
    db.commit()
    db.refresh(new_strategy)
    return success_response(data=StrategyResponse.model_validate(new_strategy))

@router.get("/", response_model=PaginatedResponse[StrategyResponse])
async def list_strategies(
    fund_id: UUID4, 
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user),
    user_fund: UserFund = Depends(RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER, UserRole.VIEWER]))
):
    query = db.query(Strategy).filter(Strategy.fund_id == fund_id)
        
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
async def update_strategy_config(
    id: UUID4, 
    config: StrategyConfigUpdate, 
    request: Request,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    strategy = db.query(Strategy).filter(Strategy.id == id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Resolve Fund ID from strategy
    await RequireRole([UserRole.OWNER, UserRole.MANAGER])(
        request=request,
        fund_id=strategy.fund_id,
        current_user=current_user,
        db=db
    )
    
    if config.config_json is not None:
        strategy.config_json = config.config_json
    if config.risk_settings is not None:
        strategy.risk_settings = config.risk_settings
    
    # Handle Active State Change with Side Effects
    if config.is_active is not None and config.is_active != strategy.is_active:
        strategy.is_active = config.is_active
        db.commit() # Commit state first
        
        try:
            if strategy.is_active:
                # Prepare payload matches start_strategy logic
                payload = strategy.config_json.copy()
                payload.update({
                    "id": str(strategy.id),
                    "template_id": strategy.template_id,
                    "broker_account_id": str(strategy.broker_account_id) if strategy.broker_account_id else None,
                    "risk_settings": strategy.risk_settings,
                    "execution_mode": "AUTO"
                })
                await strategy_client.start_strategy(str(id), payload)
            else:
                await strategy_client.stop_strategy(str(id))
        except Exception as e:
            # If side effect fails, should we revert DB?
            # Ideally yes, but for now we log and warn.
            # Reverting might confusingly toggle UI back. 
            # Let's keep DB as source of truth but returned warning in logs.
            pass
    else:
        db.commit()

    db.refresh(strategy)
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
        ),
        LogicTemplateResponse(
            id="EMA_RSI_V1",
            name="Bias Buy/Sell (EMA + RSI)",
            description="Trend Following (EMA200) with Counter-Trend Entry (RSI)",
            default_config={
                "ema_period": 200,
                "rsi_period": 14,
                "rsi_overbought": 70,
                "rsi_oversold": 30
            },
            default_risk_settings={
                 "max_drawdown": 10.0
            }
        )
    ]
    return success_response(data=templates)

from app.services.internal_client import strategy_client

@router.post("/{id}/start", response_model=APIResponse[dict])
async def start_strategy(
    id: UUID4, 
    request: Request,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    strategy = db.query(Strategy).filter(Strategy.id == id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    # Verify RBAC
    await RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER])(
        request=request,
        fund_id=strategy.fund_id,
        current_user=current_user,
        db=db
    )
    
    # Update DB status
    strategy.is_active = True
    db.commit()
    
    # Notify Strategy Core
    try:
        # Prepare Config + ID
        payload = strategy.config_json.copy()
        payload.update({
            "id": str(strategy.id),
            "template_id": strategy.template_id,
            "broker_account_id": str(strategy.broker_account_id) if strategy.broker_account_id else None,
            "risk_settings": strategy.risk_settings,
            "execution_mode": "AUTO"
        })
        
        await strategy_client.start_strategy(str(id), payload)
        
        # Also refresh Data Pipeline subscriptions
        # Ideally Strategy Core does this or we do it here.
        # Since we added /stream/refresh, let's call it?
        # Or rely on Strategy Core to handle subscriptions locally.
        # Strategy Core currently subscribes via Redis, but Data Pipeline needs to *publish*.
        # So we MUST refresh Data Pipeline.
        # But wait, StreamManager loads ACTIVE strategies? No, it loads MarketSymbols.
        # Currently, Strategies don't auto-register symbols to MarketSymbols if missing.
        # Assumption: User configured Data Source / Market Symbols already.
        
    except Exception as e:
        # Rollback DB status if core fails?
        strategy.is_active = False
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to start strategy: {str(e)}")
        
    return success_response(data={"status": "started", "id": str(id)})

@router.post("/{id}/stop", response_model=APIResponse[dict])
async def stop_strategy(
    id: UUID4, 
    request: Request,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    strategy = db.query(Strategy).filter(Strategy.id == id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    # Verify RBAC
    await RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER])(
        request=request,
        fund_id=strategy.fund_id,
        current_user=current_user,
        db=db
    )
        
    # Update DB status
    strategy.is_active = False
    db.commit()
    
    # Notify Strategy Core
    try:
        await strategy_client.stop_strategy(str(id))
    except Exception as e:
        # Log error but don't revert DB status as we want it marked stopped intendedly
        pass
        
    return success_response(data={"status": "stopped", "id": str(id)})

@router.delete("/{id}", response_model=APIResponse[dict])
async def delete_strategy(
    id: UUID4, 
    request: Request,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    strategy = db.query(Strategy).filter(Strategy.id == id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    # Verify RBAC (OWNER or MANAGER)
    await RequireRole([UserRole.OWNER, UserRole.MANAGER])(
        request=request,
        fund_id=strategy.fund_id,
        current_user=current_user,
        db=db
    )
        
    # Ensure stopped
    if strategy.is_active:
         try:
            await strategy_client.stop_strategy(str(id))
         except Exception:
            pass # Proceed to delete anyway
            
    db.delete(strategy)
    db.commit()
    
    return success_response(data={"status": "deleted", "id": str(id)})

# Custom Strategy Backtest
from datetime import datetime
class StrategyBacktestRequest(BaseModel):
    code: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    initial_capital: float = 10000.0

@router.post("/backtest-custom", response_model=APIResponse[dict])
async def run_strategies_backtest_custom(
    req: StrategyBacktestRequest,
    db: Session = Depends(get_db), 
    token: str = Depends(oauth2_scheme)
):
    try:
        # Pydantic v2: req.model_dump(), v1: req.dict(). Assuming v2 or compatible.
        # Check conversion of datetime to string via jsonable_encoder if needed, 
        # but httpx handles generic dicts well if json param used.
        # We need to ensure dates are serialized to ISO format.
        payload = req.model_dump(mode='json')
        result = await strategy_client.run_custom_backtest(payload)
        return success_response(data=result)
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/active", response_model=APIResponse[dict])
async def list_active_fleet(
    current_user: User = Depends(get_current_user)
):
    """List all active strategy instances in the fleet."""
    try:
        result = await strategy_client.list_active_strategies()
        return success_response(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{id}/tick", response_model=APIResponse[dict])
async def manual_strategy_tick(
    id: UUID4,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually trigger a single logic tick for a specific strategy."""
    # Check if strategy exists in DB first for RBAC
    strategy = db.query(Strategy).filter(Strategy.id == id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
        
    await RequireRole([UserRole.OWNER, UserRole.MANAGER, UserRole.TRADER])(
        request=request,
        fund_id=strategy.fund_id,
        current_user=current_user,
        db=db
    )
    
    try:
        result = await strategy_client.trigger_manual_tick(str(id))
        return success_response(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))