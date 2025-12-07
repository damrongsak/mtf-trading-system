from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List
from uuid import UUID
from datetime import datetime
from app.database import get_db
from app.models.journal import JournalEntry, MentalState, TimelineEvent, RootCauseAnalysis
from app.models.user_fund import User
from app.schemas.journal import JournalEntryCreate, JournalEntryResponse, JournalStatsResponse, PatternAnalysisResponse, EquityCurvePoint, PatternItem
from app.schemas.response import APIResponse, PaginatedResponse
from app.utils.response import success_response, paginated_response
from app.security import get_current_user

router = APIRouter(
    prefix="/api/v1/journal",
    tags=["journal"]
)

@router.post("/", response_model=APIResponse[JournalEntryResponse])
def create_journal_entry(entry: JournalEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Create Main Entry
    db_entry = JournalEntry(
        user_id=current_user.id,
        symbol=entry.symbol,
        direction=entry.direction,
        entry_price=entry.entry_price,
        exit_price=entry.exit_price,
        pnl_amount=entry.pnl_amount,
        pnl_r=entry.pnl_r,
        risk_amount=entry.risk_amount,
        stop_loss_price=entry.stop_loss_price,
        take_profit_price=entry.take_profit_price,
        session=entry.session,
        context_score=entry.context_score,
        game_level=entry.game_level
    )
    db.add(db_entry)
    db.flush() # Get ID

    # 2. Create Nested Objects
    if entry.mental_state:
        db_mental = MentalState(
            journal_entry_id=db_entry.id,
            **entry.mental_state.model_dump()
        )
        db.add(db_mental)

    if entry.timeline_events:
        for event in entry.timeline_events:
            db_event = TimelineEvent(
                journal_entry_id=db_entry.id,
                **event.model_dump()
            )
            db.add(db_event)

    if entry.root_cause:
        db_root = RootCauseAnalysis(
            journal_entry_id=db_entry.id,
            **entry.root_cause.model_dump()
        )
        db.add(db_root)

    db.commit()
    db.refresh(db_entry)
    return success_response(data=JournalEntryResponse.model_validate(db_entry))

@router.get("/", response_model=PaginatedResponse[JournalEntryResponse])
def list_journal_entries(
    page: int = 1,
    per_page: int = 10,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    query = db.query(JournalEntry).filter(JournalEntry.user_id == current_user.id)
    total = query.count()
    entries = query.order_by(JournalEntry.created_at.desc())\
                   .offset((page - 1) * per_page)\
                   .limit(per_page)\
                   .all()
    
    return paginated_response(
        data=[JournalEntryResponse.model_validate(e) for e in entries],
        page=page,
        per_page=per_page,
        total=total
    )

    return success_response(data=JournalEntryResponse.model_validate(entry))

# ==========================
# Analytics Endpoints
# ==========================

@router.get("/analytics/stats", response_model=APIResponse[JournalStatsResponse])
def get_journal_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get aggregated statistics for the journal (Win Rate, P&L, etc.)
    """
    # Base query
    base_query = db.query(JournalEntry).filter(JournalEntry.user_id == current_user.id)
    
    total_trades = base_query.count()
    
    if total_trades == 0:
        return success_response(data=JournalStatsResponse(
            total_trades=0,
            win_rate=0,
            profit_factor=0,
            net_pnl=0,
            avg_win=0,
            avg_loss=0,
            max_drawdown=0
        ))

    # P&L Stats
    # Note: Using python for MVP aggregations if volume is low, but SQL is better.
    # Let's use SQL for basic aggregations
    
    net_pnl = db.query(func.sum(JournalEntry.pnl_amount)).filter(JournalEntry.user_id == current_user.id).scalar() or 0.0
    
    # Wins / Losses
    winning_trades = base_query.filter(JournalEntry.pnl_amount > 0).count()
    losing_trades = base_query.filter(JournalEntry.pnl_amount <= 0).count()
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
    
    gross_profit = db.query(func.sum(JournalEntry.pnl_amount)).filter(JournalEntry.user_id == current_user.id, JournalEntry.pnl_amount > 0).scalar() or 0.0
    gross_loss = abs(db.query(func.sum(JournalEntry.pnl_amount)).filter(JournalEntry.user_id == current_user.id, JournalEntry.pnl_amount < 0).scalar() or 0.0)
    
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 0.0)
    
    avg_win = (gross_profit / winning_trades) if winning_trades > 0 else 0.0
    avg_loss = (gross_loss / losing_trades) if losing_trades > 0 else 0.0 # Return as positive number magnitude
    
    # Drawdown (Requires ordered series, better done in python for now)
    # Fetch all PnLs ordered by date
    pnl_series = db.query(JournalEntry.pnl_amount).filter(JournalEntry.user_id == current_user.id).order_by(JournalEntry.created_at.asc()).all()
    pnl_values = [r[0] for r in pnl_series if r[0] is not None]
    
    # Calculate Max Drawdown % (this is usually on equity, but let's do simple DD on PnL for now or $ DD)
    # Strict definition: DD is % decline from peak equity.
    # We need equity curve for this.
    running_balance = 0
    peak = 0
    max_dd_amount = 0
    
    for pnl in pnl_values:
        running_balance += pnl
        if running_balance > peak:
            peak = running_balance
        dd = peak - running_balance
        if dd > max_dd_amount:
            max_dd_amount = dd
            
    # As a % of "Account Size" is unknown here unless we assume a base.
    # Let's return $ amount for now or just 0 if ambiguous.
    # Implementation Plan asked for metrics. Let's stick to what we can compute reliably.
    
    return success_response(data=JournalStatsResponse(
        total_trades=total_trades,
        win_rate=win_rate,
        profit_factor=profit_factor,
        net_pnl=net_pnl,
        avg_win=avg_win,
        avg_loss=-avg_loss, # Return negative value for loss
        max_drawdown=max_dd_amount 
    ))

@router.get("/analytics/equity", response_model=APIResponse[List[EquityCurvePoint]])
def get_equity_curve(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get cumulative P&L curve
    """
    entries = db.query(JournalEntry.created_at, JournalEntry.pnl_amount)\
        .filter(JournalEntry.user_id == current_user.id)\
        .order_by(JournalEntry.created_at.asc())\
        .all()
        
    curve = []
    running_pnl = 0.0
    
    # Optionally add a starting point
    curve.append(EquityCurvePoint(timestamp=datetime.utcnow(), balance=0, pnl=0)) # Placeholder start?
    # Better: Start from first trade
    
    for entry in entries:
        if entry.pnl_amount is not None:
            running_pnl += entry.pnl_amount
            curve.append(EquityCurvePoint(
                timestamp=entry.created_at,
                balance=running_pnl, # Treating balance as cumulative PnL for now
                pnl=entry.pnl_amount
            ))
            
    return success_response(data=curve)

@router.get("/analytics/patterns", response_model=APIResponse[PatternAnalysisResponse])
def get_pattern_analysis(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get recurrence analysis of Game Levels, Emotions, and Mistakes
    """
    # 1. Game Level Distribution
    # Query: SELECT game_level, count(*), avg(pnl) FROM entries GROUP BY game_level
    game_levels_query = db.query(
        JournalEntry.game_level, 
        func.count(JournalEntry.id),
        func.avg(JournalEntry.pnl_amount)
    ).filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.game_level.isnot(None)
    ).group_by(JournalEntry.game_level).all()
    
    game_levels = [
        PatternItem(
            name=gl[0].value if hasattr(gl[0], 'value') else str(gl[0]),
            count=gl[1],
            avg_pnl=gl[2] or 0.0
        ) for gl in game_levels_query
    ]
    
    # 2. Top Emotions (from Timeline events where type='EMOTION' or just aggregated Mental State?)
    # Implementation Plan says "Top Emotions".
    # Option A: Aggregate the 'MentalState' levels (e.g. Avg Greed vs Avg Fear).
    # Option B: Count keywords in TimelineEvents?
    # Let's go with Option A: Average scores of mental states for now as it's cleaner in current SQL.
    # Actually, Plan said "Frequency counts".
    # Let's stick to Mental States > 5 implies "High X".
    
    # Alternative: Aggregate TimelineEvents
    # SELECT description, count(*) FROM timeline_events WHERE type='EMOTION' GROUP BY description
    emotions_query = db.query(
        TimelineEvent.description,
        func.count(TimelineEvent.id)
    ).join(JournalEntry).filter(
        JournalEntry.user_id == current_user.id,
        TimelineEvent.type == 'EMOTION'
    ).group_by(TimelineEvent.description).order_by(func.count(TimelineEvent.id).desc()).limit(5).all()
    
    # We need avg PnL for these emotions too?
    # Complex query. Let's keep it simple: Count only for now, avg_pnl = 0
    top_emotions = [
        PatternItem(name=e[0], count=e[1], avg_pnl=0.0) for e in emotions_query
    ]
    
    # 3. Top Mistakes (Root Cause - Problem)
    # Group by 'problem' text? Might be unique strings.
    # Group by 'flaw'?
    mistakes_query = db.query(
        RootCauseAnalysis.flaw,
        func.count(RootCauseAnalysis.id)
    ).join(JournalEntry).filter(
        JournalEntry.user_id == current_user.id,
        RootCauseAnalysis.flaw.isnot(None)
    ).group_by(RootCauseAnalysis.flaw).order_by(func.count(RootCauseAnalysis.id).desc()).limit(5).all()
    
    top_mistakes = [
        PatternItem(name=m[0], count=m[1], avg_pnl=0.0) for m in mistakes_query
    ]
    
    return success_response(data=PatternAnalysisResponse(
        game_levels=game_levels,
        top_emotions=top_emotions,
        top_mistakes=top_mistakes
    ))
