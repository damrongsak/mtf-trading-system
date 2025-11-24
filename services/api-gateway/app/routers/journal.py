from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.database import get_db
from app.models.journal import JournalEntry, MentalState, TimelineEvent, RootCauseAnalysis
from app.models.user_fund import User
from app.schemas.journal import JournalEntryCreate, JournalEntryResponse
from app.routers.auth import oauth2_scheme
from jose import jwt
from app.security import SECRET_KEY, ALGORITHM

router = APIRouter(
    prefix="/api/v1/journal",
    tags=["journal"]
)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/", response_model=JournalEntryResponse)
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
    return db_entry

@router.get("/", response_model=List[JournalEntryResponse])
def list_journal_entries(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(JournalEntry).filter(JournalEntry.user_id == current_user.id).order_by(JournalEntry.created_at.desc()).all()

@router.get("/{entry_id}", response_model=JournalEntryResponse)
def get_journal_entry(entry_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry
