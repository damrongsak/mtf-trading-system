from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import uuid
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models.strategy import Strategy
from app.models.user_fund import Fund
from app.models.backtest_profile import BacktestConfig, BacktestHistory
from app.schemas.backtest import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult
from app.schemas.response import APIResponse
from app.utils.response import success_response
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder

router = APIRouter(
    prefix="/backtest",
    tags=["backtest"],
    responses={404: {"description": "Not found"}},
)

# --- Schemas for Profile Management ---
class BacktestConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    config: BacktestRequest

class BacktestConfigResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    config: dict
    created_at: datetime

class BacktestHistorySummary(BaseModel):
    id: uuid.UUID
    status: str
    created_at: datetime
    metrics: Optional[dict]
    best_params: Optional[dict]
    execution_config: dict

# --- Profile Endpoints ---

@router.post("/configs", response_model=APIResponse[BacktestConfigResponse])
async def create_backtest_config(req: BacktestConfigCreate, db: Session = Depends(get_db)):
    """Save a new backtest configuration profile"""
    new_config = BacktestConfig(
        name=req.name,
        description=req.description,
        config_json=jsonable_encoder(req.config) # Serialize Pydantic model to JSON-compatible dict
    )
    db.add(new_config)
    db.commit()
    db.refresh(new_config)
    
    return success_response(data=BacktestConfigResponse(
        id=new_config.id,
        name=new_config.name,
        description=new_config.description,
        config=new_config.config_json,
        created_at=new_config.created_at
    ))

@router.get("/configs", response_model=APIResponse[List[BacktestConfigResponse]])
async def list_backtest_configs(db: Session = Depends(get_db)):
    """List all saved backtest configurations"""
    configs = db.query(BacktestConfig).order_by(desc(BacktestConfig.created_at)).all()
    
    return success_response(data=[
        BacktestConfigResponse(
            id=c.id,
            name=c.name,
            description=c.description,
            config=c.config_json,
            created_at=c.created_at
        ) for c in configs
    ])

from app.schemas.response import APIResponse, PaginatedResponse, Meta
import math

# ... (existing imports)

# ... (existing code)

# --- History Endpoints ---

@router.get("/history", response_model=PaginatedResponse[BacktestHistorySummary])
async def list_backtest_history(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db)
):
    """List recent backtest history with pagination"""
    query = db.query(BacktestHistory)
    total = query.count()
    total_pages = math.ceil(total / per_page)
    
    history = query.order_by(desc(BacktestHistory.created_at))\
                   .offset((page - 1) * per_page)\
                   .limit(per_page)\
                   .all()
    
    data = [
        BacktestHistorySummary(
            id=h.id,
            status=h.status,
            created_at=h.created_at,
            metrics=h.metrics,
            best_params=h.best_params,
            execution_config=h.execution_config
        ) for h in history
    ]
    
    return PaginatedResponse(
        data=data,
        meta=Meta(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages
        )
    )

# --- Execution ---

@router.post("/run", response_model=APIResponse[BacktestResponse])
async def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    """
    Trigger a backtest and save to history.
    """
    
    # 1. Resolve Strategy Configuration
    if req.strategy_id:
        strategy = db.query(Strategy).filter(Strategy.id == req.strategy_id).first()
        if not strategy:
            raise HTTPException(status_code=404, detail=f"Strategy {req.strategy_id} not found")
        
        saved_config = strategy.config_json or {}
        req.strategy_params = {**saved_config, **req.strategy_params}

    # 2. Resolve Fund/Portfolio Context
    if req.fund_id:
        fund = db.query(Fund).filter(Fund.id == req.fund_id).first()
        if not fund:
            raise HTTPException(status_code=404, detail=f"Fund {req.fund_id} not found")
        # Inject fund context here
        pass

    # 3. Create History Entry (RUNNING)
    history_entry = BacktestHistory(
        execution_config=jsonable_encoder(req), # Serialize Pydantic model to JSON-compatible dict
        status="RUNNING"
    )
    db.add(history_entry)
    db.commit()
    db.refresh(history_entry)

    try:
        # --- MOCK EXECUTION LOGIC (Replace with Strategy Core call) ---
        metrics = BacktestMetrics(
            total_return=500.0,
            total_return_percent=5.0,
            max_drawdown=200.0,
            max_drawdown_percent=2.0,
            win_rate=0.6,
            sharpe_ratio=1.5,
            total_trades=10,
            winning_trades=6,
            losing_trades=4
        )
        
        trades=[
            TradeResult(
                entry_time=datetime.utcnow(),
                exit_time=datetime.utcnow(),
                direction="LONG",
                entry_price=2000.0,
                exit_price=2050.0,
                pnl=50.0,
                pnl_percent=2.5
            )
        ]
        
        best_params = None
        all_results = None

        if req.optimization:
            best_params = {"ema_period": 20, "rsi_period": 14}
            all_results = [
                {"params": {"ema_period": 10}, "metric": 1.2},
                {"params": {"ema_period": 20}, "metric": 1.5},
            ]
        # ---------------------------------------------------------------

        # 4. Update History Entry (COMPLETED)
        history_entry.status = "COMPLETED"
        history_entry.metrics = metrics.dict()
        history_entry.best_params = best_params
        db.commit()

        response_data = BacktestResponse(
            id=str(history_entry.id), # Use DB ID
            status="COMPLETED",
            metrics=metrics,
            trades=trades,
            best_params=best_params,
            all_results=all_results
        )
        
        return success_response(data=response_data)

    except Exception as e:
        # Handle Failure
        history_entry.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
