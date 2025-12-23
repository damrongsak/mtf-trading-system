from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timedelta
from typing import List, Optional

from app.database import get_db
from app.security import get_current_user
from app.models.user_fund import User
from app.models.trade import Trade, TradeStatus
from app.models.strategy_run import StrategyRun
from app.models.strategy import Strategy

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    strategy_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated dashboard statistics, optionally filtered by strategy_id.
    """
    # Base query for closed trades
    base_query = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED)
    
    if strategy_id:
        # Join with StrategyRun to filter by strategy_id
        base_query = base_query.join(StrategyRun, Trade.strategy_run_id == StrategyRun.run_id)\
                               .filter(StrategyRun.strategy_id == strategy_id)
    
    # Calculate totals
    total_trades = base_query.count()
    
    if total_trades == 0:
         return {
            "total_pnl": 0.0,
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "open_positions": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0
        }

    # Calculate PnL (Using subquery or same filter)
    total_pnl = base_query.with_entities(func.sum(Trade.pnl_usd)).scalar() or 0.0
    
    # Win Rate
    winning_trades = base_query.filter(Trade.pnl_usd > 0).count()
    losing_trades = base_query.filter(Trade.pnl_usd <= 0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Open Positions
    open_query = db.query(Trade).filter(Trade.status == TradeStatus.OPEN)
    if strategy_id:
        open_query = open_query.join(StrategyRun, Trade.strategy_run_id == StrategyRun.run_id)\
                               .filter(StrategyRun.strategy_id == strategy_id)
    open_positions = open_query.count()
    
    # Averages
    avg_win = base_query.filter(Trade.pnl_usd > 0).with_entities(func.avg(Trade.pnl_usd)).scalar() or 0.0
    avg_loss = base_query.filter(Trade.pnl_usd <= 0).with_entities(func.avg(Trade.pnl_usd)).scalar() or 0.0

    return {
        "total_pnl": float(total_pnl),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": float(win_rate),
        "open_positions": open_positions,
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss)
    }

@router.get("/equity-curve")
async def get_equity_curve(
    days: int = 30,
    strategy_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily equity curve data for the last N days, optionally filtered by strategy_id.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all closed trades in the period, ordered by exit time
    query = db.query(Trade).filter(
        Trade.status == TradeStatus.CLOSED,
        Trade.exit_timestamp >= start_date
    )
    
    if strategy_id:
        query = query.join(StrategyRun, Trade.strategy_run_id == StrategyRun.run_id)\
                     .filter(StrategyRun.strategy_id == strategy_id)
                     
    trades = query.order_by(Trade.exit_timestamp).all()
    
    # Aggregate by day
    daily_pnl = {}
    
    # Initialize with 0 for all days in range to ensure continuity
    for i in range(days + 1):
        day_str = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        daily_pnl[day_str] = 0.0
        
    for trade in trades:
        if trade.exit_timestamp:
            day_str = trade.exit_timestamp.strftime('%Y-%m-%d')
            if day_str in daily_pnl:
                 daily_pnl[day_str] += float(trade.pnl_usd or 0)

    # Create cumulative curve
    curve_data = []
    running_balance = 0.0 # Assuming starting from 0 relative PnL for this view
    
    sorted_days = sorted(daily_pnl.keys())
    for day in sorted_days:
        running_balance += daily_pnl[day]
        curve_data.append({
            "date": day,
            "equity": running_balance,
            "daily_pnl": daily_pnl[day]
        })
        
    return curve_data

@router.get("/performance")
async def get_strategy_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = db.query(
        Trade.strategy_name,
        func.count(Trade.trade_id).label('total_trades'),
        func.sum(Trade.pnl_usd).label('total_pnl'),
        func.sum(case((Trade.pnl_usd > 0, 1), else_=0)).label('wins')
    ).filter(
        Trade.status == TradeStatus.CLOSED
    ).group_by(Trade.strategy_name).all()
    
    performance = []
    for r in results:
        total = r.total_trades
        wins = r.wins
        win_rate = (wins / total * 100) if total > 0 else 0.0
        
        performance.append({
            "strategy_name": r.strategy_name,
            "total_trades": total,
            "total_pnl": float(r.total_pnl or 0),
            "win_rate": float(win_rate)
        })
        
    return performance