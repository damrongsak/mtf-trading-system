from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from app.database import get_db
from app.models.journal import JournalEntry, MentalState, TimelineEvent, RootCauseAnalysis
from app.models.trade import Trade
from app.models.user import User
from app.schemas.journal import JournalEntryCreate, JournalEntryResponse, JournalStatsResponse, PatternAnalysisResponse, EquityCurvePoint, PatternItem, JournalImportRequest, JournalImportResponse
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
    symbol: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    query = db.query(JournalEntry).filter(JournalEntry.user_id == current_user.id)

    # Apply Filters
    if symbol:
        query = query.filter(JournalEntry.symbol.ilike(f"%{symbol}%"))
    
    if direction and direction != "ALL":
        query = query.filter(JournalEntry.direction == direction)
        
    if date_from:
        query = query.filter(JournalEntry.created_at >= date_from)
        
    if date_to:
        # Include the whole end day
        query = query.filter(JournalEntry.created_at <= date_to)

    if search:
        # Generic search: currently matching symbol. 
        # Could extend to match notes in nested tables if needed.
        query = query.filter(JournalEntry.symbol.ilike(f"%{search}%"))

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

@router.get("/{journal_id}", response_model=APIResponse[JournalEntryResponse])
def get_journal_entry(
    journal_id: UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == journal_id, 
        JournalEntry.user_id == current_user.id
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
        
    return success_response(data=JournalEntryResponse.model_validate(entry))

@router.put("/{journal_id}", response_model=APIResponse[JournalEntryResponse])
def update_journal_entry(
    journal_id: UUID,
    update_data: JournalEntryCreate, # Using Create schema as Update for now
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == journal_id,
        JournalEntry.user_id == current_user.id
    ).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    
    # 1. Update Main Fields
    # Iterate over fields in the schema, exclude nested models
    main_fields = update_data.model_dump(exclude={'mental_state', 'timeline_events', 'root_cause'}, exclude_unset=True)
    for key, value in main_fields.items():
        setattr(entry, key, value)

    # 2. Update Nested: MentalState (One-to-One)
    if update_data.mental_state:
        if entry.mental_state:
            # Update existing
            for key, value in update_data.mental_state.model_dump(exclude_unset=True).items():
                setattr(entry.mental_state, key, value)
        else:
            # Create new
            new_mental = MentalState(journal_entry_id=entry.id, **update_data.mental_state.model_dump())
            db.add(new_mental)

    # 3. Update Nested: RootCause (One-to-One)
    if update_data.root_cause:
        if entry.root_cause:
            # Update existing
            for key, value in update_data.root_cause.model_dump(exclude_unset=True).items():
                setattr(entry.root_cause, key, value)
        else:
            # Create new
            new_root = RootCauseAnalysis(journal_entry_id=entry.id, **update_data.root_cause.model_dump())
            db.add(new_root)

    # 4. Update Nested: TimelineEvents (One-to-Many)
    # Strategy: Delete all and recreate? Or smart update? 
    # For simplicity and given the low volume, Delete All + Recreate is safest to ensure order/integrity.
    if update_data.timeline_events is not None:
        # Check if list is empty or has items. If explicit list provided, replace.
        # Remove old events
        db.query(TimelineEvent).filter(TimelineEvent.journal_entry_id == entry.id).delete()
        
        # Add new events
        for event in update_data.timeline_events:
            new_event = TimelineEvent(journal_entry_id=entry.id, **event.model_dump())
            db.add(new_event)

    db.commit()
    db.refresh(entry)
    return success_response(data=JournalEntryResponse.model_validate(entry))

@router.delete("/{journal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_journal_entry(
    journal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == journal_id,
        JournalEntry.user_id == current_user.id
    ).first()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found"
        )
    
    db.delete(entry)
    db.commit()
    db.delete(entry)
    db.commit()
    return None

@router.post("/import", response_model=APIResponse[JournalImportResponse])
def import_trades(
    request: JournalImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Import trades into the journal. Skips duplicates.
    """
    # 1. Identify duplicates
    existing_entries = db.query(JournalEntry.trade_id).filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.trade_id.in_(request.trade_ids)
    ).all()
    
    existing_trade_ids = {e[0] for e in existing_entries}
    
    # 2. Filter new IDs
    new_trade_ids = [tid for tid in request.trade_ids if tid not in existing_trade_ids]
    
    skipped_count = len(request.trade_ids) - len(new_trade_ids)
    
    if not new_trade_ids:
        return success_response(data=JournalImportResponse(
            imported_count=0,
            skipped_count=skipped_count,
            message="No new trades to import."
        ))

    # 3. Fetch Trade details
    trades = db.query(Trade).filter(Trade.trade_id.in_(new_trade_ids)).all()
    
    imported_count = 0
    for trade in trades:
        # Calculate Realized R if possible
        calculated_r = 0.0
        if trade.pnl_usd and trade.risk_usd and trade.risk_usd != 0:
            calculated_r = float(trade.pnl_usd) / float(trade.risk_usd)
            
        new_entry = JournalEntry(
            user_id=current_user.id,
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            direction=trade.direction.value if hasattr(trade.direction, 'value') else str(trade.direction),
            entry_price=float(trade.entry_price) if trade.entry_price else None,
            exit_price=float(trade.exit_price) if trade.exit_price else None,
            pnl_amount=float(trade.pnl_usd) if trade.pnl_usd else None,
            pnl_r=calculated_r,
            risk_amount=float(trade.risk_usd) if trade.risk_usd else None,
            stop_loss_price=float(trade.sl_price) if trade.sl_price else None,
            take_profit_price=float(trade.tp_price) if trade.tp_price else None,
            session="Imported",
            created_at=trade.created_at if trade.created_at else datetime.now(timezone.utc)
        )
        db.add(new_entry)
        imported_count += 1
        
    db.commit()
    
    
    return success_response(data=JournalImportResponse(
        imported_count=imported_count,
        skipped_count=skipped_count,
        message=f"Successfully imported {imported_count} trades. Skipped {skipped_count} duplicates."
    ))

# ==========================
# Internal AI Analyst API
# ==========================

@router.get("/internal/memory/pending-trades")
def get_pending_ai_trades(
    limit: int = 5,
    db: Session = Depends(get_db)
    # Note: A real prod system might require internal API key verification here,
    # but for this MVP, we omit strictly enforcing a service token parsing on this internal route
    # or rely on an upstream gateway rule.
):
    """
    Internal endpoint: Fetches closed trades that do NOT have an AI-generated journal entry yet.
    """
    # Find trades that do NOT have a corresponding JournalEntry with is_ai_generated=True
    # Subquery defining Trade IDs that already have an AI Journal
    ai_journaled_subq = db.query(JournalEntry.trade_id).filter(
        JournalEntry.is_ai_generated == True,
        JournalEntry.trade_id.isnot(None)
    ).subquery()

    # Query trades NOT IN the subquery
    pending_trades = db.query(Trade).filter(
        Trade.trade_id.notin_(ai_journaled_subq)
    ).order_by(Trade.created_at.desc()).limit(limit).all()

    # We return raw dicts for easy JSON parsing by the AI Agent
    result = []
    for t in pending_trades:
        result.append({
            "trade_id": str(t.trade_id),
            "symbol": t.symbol,
            "direction": t.direction.value if hasattr(t.direction, 'value') else str(t.direction),
            "entry_price": float(t.entry_price) if t.entry_price else None,
            "exit_price": float(t.exit_price) if t.exit_price else None,
            "pnl_usd": float(t.pnl_usd) if t.pnl_usd else None,
            "risk_usd": float(t.risk_usd) if t.risk_usd else None,
            "strategy": t.strategy_name,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })

    return success_response(data=result)

@router.post("/internal/memory/save-insight")
def save_ai_insight(
    payload: dict, # Simple dict for internal API
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Saves an AI-generated lesson as a JournalEntry.
    """
    trade_id = payload.get("trade_id")
    ai_insight = payload.get("ai_insight")
    game_level = payload.get("game_level", "B_GAME")

    if not trade_id or not ai_insight:
        raise HTTPException(status_code=400, detail="Missing trade_id or ai_insight")

    # Verify Trade exists
    trade = db.query(Trade).filter(Trade.trade_id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    # Check if entry already exists (idempotency & compatibility with auto-load)
    existing = db.query(JournalEntry).filter(
        JournalEntry.trade_id == trade_id
    ).first()
    
    if existing:
        # Update existing entry (could be a human draft or previous AI entry)
        existing.ai_insight = ai_insight
        existing.game_level = game_level
        existing.is_ai_generated = True # Mark as AI-analyzed
        db.commit()
        return success_response(data={"journal_id": str(existing.id), "status": "updated"})

    # Resolve user_id from the linked broker account or strategy run
    user_id = None
    if hasattr(trade, 'broker_account_id') and trade.broker_account_id:
        from app.models.broker_account import BrokerAccount
        account = db.query(BrokerAccount).filter(BrokerAccount.id == trade.broker_account_id).first()
        if account and hasattr(account, 'fund_id') and account.fund_id:
            from app.models.user_fund import UserFund
            uf = db.query(UserFund).filter(UserFund.fund_id == account.fund_id).first()
            if uf:
                user_id = uf.user_id

    # Fallback for system-generated trades or if no fund is attached
    if not user_id:
        from app.models.user import User
        first_user = db.query(User).first()
        if first_user:
            user_id = first_user.id
            
    if not user_id:
        raise HTTPException(status_code=500, detail="Could not resolve user_id for JournalEntry")

    # Create new AI Journal Entry linked to the Trade
    new_entry = JournalEntry(
        user_id=user_id, # Link it to the user who made the trade
        trade_id=trade.trade_id,
        symbol=trade.symbol,
        direction=trade.direction.value if hasattr(trade.direction, 'value') else str(trade.direction),
        entry_price=float(trade.entry_price) if trade.entry_price else None,
        exit_price=float(trade.exit_price) if trade.exit_price else None,
        pnl_amount=float(trade.pnl_usd) if trade.pnl_usd else None,
        session="AI_Analyst",
        game_level=game_level,
        is_ai_generated=True,
        ai_insight=ai_insight
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return success_response(data={"journal_id": str(new_entry.id), "status": "created"})

@router.post("/internal/memory/auto-load-sync")
async def manual_auto_load_journal():
    """Manual trigger for auto-loading journal entries from trades (for verification/sync)"""
    from app.scheduler import auto_load_trades_to_journal_job
    try:
        await auto_load_trades_to_journal_job()
        return success_response(message="Auto-load sync triggered successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    curve.append(EquityCurvePoint(timestamp=datetime.now(timezone.utc), balance=0, pnl=0)) # Placeholder start?
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
