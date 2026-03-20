from fastapi import APIRouter, HTTPException, Depends, Body
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
from app.schemas.backtest import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult, StrategyBacktestRequest
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from app.services.internal_client import strategy_client

import logging

logger = logging.getLogger(__name__)

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
        # Check if strategy_id is a valid UUID before querying
        is_valid_uuid = False
        try:
            if isinstance(req.strategy_id, uuid.UUID):
                is_valid_uuid = True
            else:
                uuid.UUID(str(req.strategy_id))
                is_valid_uuid = True
        except ValueError:
            is_valid_uuid = False

        if is_valid_uuid:
            strategy = db.query(Strategy).filter(Strategy.id == req.strategy_id).first()
            if not strategy:
                raise HTTPException(status_code=404, detail=f"Strategy {req.strategy_id} not found")
            
            saved_config = strategy.config_json or {}
            req.strategy_params = {**saved_config, **req.strategy_params}
        else:
            # Assume it's a template name or string ID handled directly by Strategy Core
            logger.info(f"Using strategy template/string ID: {req.strategy_id}")
            pass

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
        # Prepare payload
        # Ensure dates are serialized
        payload = jsonable_encoder(req)
        
        # Call Strategy Core
        result = await strategy_client.run_backtest(payload)
        
        # 4. Update History Entry (COMPLETED)
        history_entry.status = "COMPLETED"
        history_entry.metrics = result.get('metrics')
        history_entry.best_params = result.get('best_params')
        
        # Store execution duration or other metadata if needed
        # history_entry.completed_at = datetime.utcnow() # If model has it
        
        db.commit()

        return success_response(data=result)

    except Exception as e:
        # Handle Failure
        history_entry.status = "FAILED"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/optimize")
async def run_optimization(req: dict = Body(...), db: Session = Depends(get_db)):
    """
    Proxy optimization request to Strategy Core.
    """
    try:
        # We accept a dict/Body to be flexible, or we could use the strict Optimization schemas
        # Forward to Strategy Core
        result = await strategy_client.run_optimization(req)
        return success_response(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/custom", response_model=APIResponse[BacktestResponse])
async def run_custom_backtest(req: StrategyBacktestRequest, db: Session = Depends(get_db)):
    """
    Run a custom user-defined strategy.
    """
    try:
        # Pass payload to Strategy Core
        payload = jsonable_encoder(req)
        result = await strategy_client.run_custom_backtest(payload)
        return success_response(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/monte-carlo")
async def run_monte_carlo(req: dict = Body(...), db: Session = Depends(get_db)):
    """
    Proxy Monte Carlo request to Strategy Core.
    """
    try:
        result = await strategy_client.run_monte_carlo(req)
        return success_response(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{backtest_id}", response_model=APIResponse[BacktestResponse])
async def get_backtest_results(backtest_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Get results of a specific backtest from history.
    """
    history = db.query(BacktestHistory).filter(BacktestHistory.id == backtest_id).first()
    if not history:
        raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
    
    # Reconstruct BacktestResponse structure
    result = {
        "id": str(history.id),
        "status": history.status,
        "metrics": history.metrics,
        "trades": [], # Trades might be stored separately or in metrics, for now empty or from DB
        "best_params": history.best_params
    }
    
    return success_response(data=result)
