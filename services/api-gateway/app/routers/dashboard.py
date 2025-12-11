from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, case
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.database import get_db
from app.models.trade import Trade, TradeStatus
from app.security import get_current_user
from app.models.user_fund import User

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"],
    responses={404: {"description": "Not found"}},
)

@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get aggregated dashboard statistics.
    """
    # Base query for closed trades
    base_query = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED)
    
    # Calculate totals
    total_trades = base_query.count()
    
    # Calculate PnL
    total_pnl = db.query(func.sum(Trade.pnl_usd)).filter(Trade.status == TradeStatus.CLOSED).scalar() or 0.0
    
    # Win Rate
    winning_trades = base_query.filter(Trade.pnl_usd > 0).count()
    losing_trades = base_query.filter(Trade.pnl_usd <= 0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    # Open Positions
    open_positions = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).count()
    
    # Averages
    avg_win = db.query(func.avg(Trade.pnl_usd)).filter(Trade.status == TradeStatus.CLOSED, Trade.pnl_usd > 0).scalar() or 0.0
    avg_loss = db.query(func.avg(Trade.pnl_usd)).filter(Trade.status == TradeStatus.CLOSED, Trade.pnl_usd <= 0).scalar() or 0.0

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get daily equity curve data for the last N days.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get all closed trades in the period, ordered by exit time
    trades = db.query(Trade).filter(
        Trade.status == TradeStatus.CLOSED,
        Trade.exit_timestamp >= start_date
    ).order_by(Trade.exit_timestamp).all()
    
    # Aggregate by day
    daily_pnl = {}
    cumulative_pnl = 0.0
    
    # Initialize with 0 for all days in range to ensure continuity
    for i in range(days + 1):
        day_str = (start_date + timedelta(days=i)).strftime('%Y-%m-%d')
        daily_pnl[day_str] = 0.0

    # Sum up PnL per day
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
    """
    Get performance metrics grouped by strategy.
    """
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
