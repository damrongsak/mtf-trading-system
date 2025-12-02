from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.journal import JournalEntry, MentalState, TimelineEvent, RootCauseAnalysis
from app.models.user_fund import User
from app.schemas.journal import JournalEntryCreate, JournalEntryResponse
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

@router.get("/{entry_id}", response_model=APIResponse[JournalEntryResponse])
def get_journal_entry(entry_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return success_response(data=JournalEntryResponse.model_validate(entry))
