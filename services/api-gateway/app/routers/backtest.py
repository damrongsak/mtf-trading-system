from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
import uuid
from app.schemas.backtest import BacktestRequest, BacktestResponse, BacktestMetrics, TradeResult
from app.schemas.response import APIResponse
from app.utils.response import success_response

router = APIRouter(
    prefix="/backtest",
    tags=["backtest"],
    responses={404: {"description": "Not found"}},
)

@router.post("/run", response_model=APIResponse[BacktestResponse])
async def run_backtest(req: BacktestRequest):
    """
    Trigger a backtest.
    Currently returns a mock response until Strategy Core is integrated.
    """
    # Mock response
    data = BacktestResponse(
        id=str(uuid.uuid4()),
        status="COMPLETED",
        metrics=BacktestMetrics(
            total_return=500.0,
            total_return_percent=5.0,
            max_drawdown=200.0,
            max_drawdown_percent=2.0,
            win_rate=0.6,
            total_trades=10,
            winning_trades=6,
            losing_trades=4
        ),
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
    )
    return success_response(data=data)

@router.get("/results/{backtest_id}", response_model=APIResponse[BacktestResponse])
async def get_backtest_results(backtest_id: str):
    """
    Get results of a specific backtest.
    """
    # Mock response
    data = BacktestResponse(
        id=backtest_id,
        status="COMPLETED",
        metrics=BacktestMetrics(
            total_return=500.0,
            total_return_percent=5.0,
            max_drawdown=200.0,
            max_drawdown_percent=2.0,
            win_rate=0.6,
            total_trades=10,
            winning_trades=6,
            losing_trades=4
        ),
        trades=[]
    )
    return success_response(data=data)
