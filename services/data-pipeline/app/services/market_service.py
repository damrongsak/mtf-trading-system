from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.repositories.market_repository import MarketRepository
from app.schemas import MarketSymbolResponse, MarketSymbolUpdate
from app.models.market import MarketSymbol
from fastapi import HTTPException

class MarketService:
    @staticmethod
    def get_active_symbols(db: Session, broker: str) -> List[MarketSymbolResponse]:
        repo = MarketRepository(db)
        symbols = repo.get_active_symbols(broker)
        # Pydantic conversion happens in Route via response_model, 
        # but explicit conversion is safer for Service pattern if we want pure DTOs.
        # For now, returning ORM objects works with from_attributes=True in schema.
        return symbols

    @staticmethod
    def update_status(db: Session, symbol_id: UUID, update_data: MarketSymbolUpdate) -> MarketSymbolResponse:
        repo = MarketRepository(db)
        symbol = repo.get_by_id(symbol_id)
        if not symbol:
            raise HTTPException(status_code=404, detail="Symbol not found")
            
        updated_symbol = repo.update_status(symbol, update_data.is_active)
        return updated_symbol
