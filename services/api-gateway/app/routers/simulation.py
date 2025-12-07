from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.utils.response import success_response
from app.schemas.response import APIResponse
from pydantic import BaseModel
import httpx
import os
from typing import Optional

router = APIRouter(
    prefix="/api/v1/simulation",
    tags=["simulation"]
)

# Define schemas here or import from shared schemas if available
# For now, repeating minimal definitions to avoid coupling if shared lib not present

class MarketRegime(BaseModel):
    trend: str # 'NO_TREND', 'UPTREND', 'DOWNTREND'
    volatility: int # 1-10
    noise: str # 'GAUSSIAN', 'FAT_TAIL'

class GridConfig(BaseModel):
    step_size: float
    grid_levels: int
    initial_lot: float
    use_compound: bool
    stop_loss_pct: float

class SimulationRequest(BaseModel):
    regime: MarketRegime
    grid: GridConfig
    iterations: int = 1

class SimulationMetrics(BaseModel):
    total_pnl: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    profit_factor: float

class EquityPoint(BaseModel):
    timestamp: str
    value: float

class SimulationResponse(BaseModel):
    id: str
    metrics: SimulationMetrics
    equity_curve: List[EquityPoint]
    status: str

# Config
STRATEGY_CORE_URL = os.getenv("STRATEGY_CORE_URL", "http://strategy-core:8002")

@router.post("/", response_model=APIResponse[SimulationResponse])
async def run_simulation(req: SimulationRequest):
    """
    Run a simulation via the Strategy Core service.
    """
    async with httpx.AsyncClient() as client:
        try:
            # Proxy request to strategy-core
            response = await client.post(
                f"{STRATEGY_CORE_URL}/simulate",
                json=req.model_dump(),
                timeout=30.0 # Sim can take time
            )
            
            if response.status_code != 200:
                error_detail = "Unknown error from strategy core"
                try:
                    error_detail = response.json().get("detail", response.text)
                except:
                    pass
                raise HTTPException(status_code=response.status_code, detail=error_detail)
            
            data = response.json()
            # Wrap in standard APIResponse
            return success_response(data=data)
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Strategy Core Service unavailable: {str(e)}")
