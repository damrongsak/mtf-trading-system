from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
import uuid

from app.database import get_db
from app.models.market import MarketCategory, MarketSymbol

router = APIRouter(tags=["market-data"])

# --- Schemas ---
class SymbolSchema(BaseModel):
    id: Optional[uuid.UUID] = None
    symbol: str
    display_name: Optional[str] = None
    order_index: int = 0
    broker: Optional[str] = None # Name of the data source

    model_config = ConfigDict(from_attributes=True)

class CategorySchema(BaseModel):
    id: Optional[uuid.UUID] = None
    name: str
    order_index: int = 0
    items: List[SymbolSchema] = []
    
    model_config = ConfigDict(from_attributes=True)

class CreateCategorySchema(BaseModel):
    name: str

class AddSymbolSchema(BaseModel):
    symbol: str
    display_name: Optional[str] = None

# --- Endpoints ---

@router.get("/market/categories", response_model=List[CategorySchema])
def get_categories(db: Session = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    cats = db.query(MarketCategory).filter(MarketCategory.is_active == True).options(
        joinedload(MarketCategory.items).joinedload(MarketSymbol.data_source)
    ).order_by(MarketCategory.order_index).all()
    return cats

@router.post("/market/categories", response_model=CategorySchema)
def create_category(payload: CreateCategorySchema, db: Session = Depends(get_db)):
    # Check if exists
    existing = db.query(MarketCategory).filter(MarketCategory.name == payload.name).first()
    if existing:
         raise HTTPException(status_code=400, detail="Category already exists")
    
    cat = MarketCategory(name=payload.name)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat

@router.post("/market/categories/{category_id}/symbols", response_model=SymbolSchema)
def add_symbol(category_id: uuid.UUID, payload: AddSymbolSchema, db: Session = Depends(get_db)):
    cat = db.query(MarketCategory).filter(MarketCategory.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
        
    sym = MarketSymbol(
        category_id=category_id,
        symbol=payload.symbol,
        display_name=payload.display_name
    )
    db.add(sym)
    db.commit()
    db.refresh(sym)
    return sym
