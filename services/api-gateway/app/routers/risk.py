from fastapi import APIRouter, HTTPException, Depends, Body, Query
from app.schemas.risk import RiskCheckRequest, RiskCheckResponse, FundRiskConfig, RiskAdjustmentRequest, KillSwitchRequest
from app.schemas.response import APIResponse
from app.utils.response import success_response
from app.security import get_current_user
from app.models.user import User
from app.models.user_fund import Fund, UserFund
from app.database import get_db
from sqlalchemy.orm import Session
import httpx
import os
import json
from uuid import UUID

from app.utils.http_client import get_internal_client
from app.utils.redis_client import get_redis_client

router = APIRouter(
    prefix="/api/v1/risk",
    tags=["risk"]
)
EXECUTION_SERVICE_URL = os.getenv("EXECUTION_SERVICE_URL", "http://execution:8000")
STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8000")

@router.post("/check", response_model=APIResponse[RiskCheckResponse])
async def check_risk(
    req: RiskCheckRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Proxy risk check to the Strategy Core Service.
    """
    async with await get_internal_client() as client:
        try:
            # Forward request to strategy-core service
            response = await client.post(
                f"{STRATEGY_CORE_URL}/api/v1/risk/check", 
                json=req.model_dump(mode='json'),
                timeout=5.0
            )
            response.raise_for_status()
            
            resp_data = response.json()
            if "data" in resp_data:
                return success_response(data=resp_data["data"])
            else:
                return success_response(data=resp_data)
                
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"Risk service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"Risk service error: {exc.response.text}")

@router.get("/fund/{fund_id}/config", response_model=APIResponse[FundRiskConfig])
async def get_fund_risk_config(
    fund_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get institutional risk configuration for a specific fund."""
    # Verify access
    user_fund = db.query(UserFund).filter(UserFund.fund_id == fund_id, UserFund.user_id == current_user.id).first()
    if not user_fund:
        raise HTTPException(status_code=403, detail="Access denied to this fund")
    
    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")
        
    # Check current kill switch status from Redis
    rc = await get_redis_client()
    is_halted = await rc.get(f"fund:{fund_id}:halted") == "1"
    
    return success_response(data=FundRiskConfig(
        fund_id=fund.id,
        max_drawdown_threshold=fund.max_drawdown_threshold,
        gross_exposure_limit=fund.gross_exposure_limit,
        net_exposure_limit=fund.net_exposure_limit,
        kill_switch_active=is_halted
    ))

@router.patch("/fund/{fund_id}/config", response_model=APIResponse[FundRiskConfig])
async def update_fund_risk_config(
    fund_id: UUID,
    req: RiskAdjustmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update institutional risk configuration for a specific fund (Admin/Manager only)."""
    user_fund = db.query(UserFund).filter(UserFund.fund_id == fund_id, UserFund.user_id == current_user.id).first()
    if not user_fund or user_fund.role not in ["OWNER", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Only Owners or Managers can update risk config")

    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    if req.max_drawdown_threshold is not None:
        fund.max_drawdown_threshold = req.max_drawdown_threshold
    if req.gross_exposure_limit is not None:
        fund.gross_exposure_limit = req.gross_exposure_limit
    if req.net_exposure_limit is not None:
        fund.net_exposure_limit = req.net_exposure_limit
    
    db.commit()
    db.refresh(fund)
    
    # Broadcast change if needed (EquityGuardian polling or event bus)
    
    return success_response(data=FundRiskConfig(
        fund_id=fund.id,
        max_drawdown_threshold=fund.max_drawdown_threshold,
        gross_exposure_limit=fund.gross_exposure_limit,
        net_exposure_limit=fund.net_exposure_limit,
        kill_switch_active=False # Toggle handled separately
    ))

@router.post("/fund/{fund_id}/kill-switch", response_model=APIResponse[bool])
async def toggle_fund_kill_switch(
    fund_id: UUID,
    req: KillSwitchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Immediately halt or resume all trading for a specific fund."""
    user_fund = db.query(UserFund).filter(UserFund.fund_id == fund_id, UserFund.user_id == current_user.id).first()
    if not user_fund or user_fund.role not in ["OWNER", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Only Owners or Managers can toggle kill switch")

    rc = await get_redis_client()
    key = f"fund:{fund_id}:halted"
    
    if req.active:
        await rc.set(key, "1")
        # Optional: Publish event
        await rc.publish("system:events", json.dumps({
            "event": "FUND_HALTED",
            "fund_id": str(fund_id),
            "reason": req.reason or "Manual kill-switch activated"
        }))
    else:
        await rc.delete(key)
        await rc.publish("system:events", json.dumps({
            "event": "FUND_RESUMED",
            "fund_id": str(fund_id)
        }))

    return success_response(data=req.active, message=f"Fund {'halted' if req.active else 'resumed'} successfully")

@router.post("/fund/{fund_id}/apply-recommendation", response_model=APIResponse[FundRiskConfig])
async def apply_ai_risk_recommendation(
    fund_id: UUID,
    recommendation: dict = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Applies an AI-suggested risk rebalancing recommendation to a fund.
    """
    user_fund = db.query(UserFund).filter(UserFund.fund_id == fund_id, UserFund.user_id == current_user.id).first()
    if not user_fund or user_fund.role not in ["OWNER", "MANAGER"]:
        raise HTTPException(status_code=403, detail="Only Owners or Managers can apply recommendations")

    fund = db.query(Fund).filter(Fund.id == fund_id).first()
    if not fund:
        raise HTTPException(status_code=404, detail="Fund not found")

    # Update fields from recommendation
    previous_config = {
        "risk_percentage": float(fund.risk_percentage) if fund.risk_percentage else 0,
        "max_drawdown_threshold": float(fund.max_drawdown_threshold) if fund.max_drawdown_threshold else 0
    }

    if "risk_percentage" in recommendation:
        fund.risk_percentage = recommendation["risk_percentage"]
    if "max_drawdown_threshold" in recommendation:
        fund.max_drawdown_threshold = recommendation["max_drawdown_threshold"]
    
    db.commit()
    db.refresh(fund)

    applied_config = {
        "risk_percentage": float(fund.risk_percentage) if fund.risk_percentage else 0,
        "max_drawdown_threshold": float(fund.max_drawdown_threshold) if fund.max_drawdown_threshold else 0
    }

    # Record in rebalance_history for audit
    from app.models.rebalance_history import RebalanceHistory
    import uuid as uuid_mod
    history = RebalanceHistory(
        id=uuid_mod.uuid4(),
        fund_id=fund_id,
        trigger_type="MANUAL",
        previous_config=previous_config,
        applied_config=applied_config,
        reasoning=recommendation.get("reasoning", "Manual AI recommendation apply"),
        applied_by=str(current_user.id)
    )
    db.add(history)
    db.commit()
    
    # Broadcast change to Execution Service via Redis
    rc = await get_redis_client()
    await rc.publish("system:events", json.dumps({
        "event": "RISK_REBALANCE_APPLIED",
        "fund_id": str(fund_id),
        "applied_by": str(current_user.id)
    }))
    
    return success_response(data=FundRiskConfig(
        fund_id=fund.id,
        max_drawdown_threshold=fund.max_drawdown_threshold,
        gross_exposure_limit=fund.gross_exposure_limit,
        net_exposure_limit=fund.net_exposure_limit,
        kill_switch_active=False
    ))

@router.post("/ai-review", response_model=APIResponse[dict])
async def trigger_ai_risk_review(
    fund_id: UUID = Body(..., embed=True),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers an AI-driven risk rebalancing review for a specific fund.
    Calls the AI Analyst service to perform the analysis.
    """
    AI_ANALYST_URL = os.getenv("AI_ANALYST_URL", "http://ai-analyst:8000")
    
    async with await get_internal_client() as client:
        try:
            # We use the generic agent orchestration endpoint or a specialized one
            # For simplicity, we call the agents/risk-rebalacer endpoint if it exists,
            # or just use the main agents endpoint with a specific intent.
            payload = {
                "message": f"Review risk for fund {fund_id}",
                "context": {
                    "active_fund_id": str(fund_id)
                }
            }
            
            response = await client.post(
                f"{AI_ANALYST_URL}/api/v1/agents/orchestrate",
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            return success_response(data=response.json().get("data", {}))
            
        except httpx.RequestError as exc:
            raise HTTPException(status_code=503, detail=f"AI service unreachable: {exc}")
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=exc.response.status_code, detail=f"AI service error: {exc.response.text}")


@router.get("/rebalance-history", response_model=APIResponse[list])
async def get_rebalance_history(
    fund_id: UUID = Query(None, description="Filter by fund ID"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns paginated rebalance history for audit purposes.
    Security: Only returns records for funds the user has access to via user_funds table.
    """
    from app.models.rebalance_history import RebalanceHistory
    from app.models.user_fund import UserFund
    from sqlalchemy import desc

    # Start query with security join
    query = db.query(RebalanceHistory).join(
        UserFund, UserFund.fund_id == RebalanceHistory.fund_id
    ).filter(UserFund.user_id == current_user.id)

    if fund_id:
        # Additionally filter by specific fund_id if requested
        query = query.filter(RebalanceHistory.fund_id == fund_id)
    
    records = query.order_by(desc(RebalanceHistory.created_at)).limit(limit).all()
    
    result = []
    for r in records:
        result.append({
            "id": str(r.id),
            "fund_id": str(r.fund_id),
            "trigger_type": r.trigger_type,
            "drift_score": r.drift_score,
            "previous_config": r.previous_config,
            "applied_config": r.applied_config,
            "reasoning": r.reasoning,
            "applied_by": r.applied_by,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    return success_response(data=result)
