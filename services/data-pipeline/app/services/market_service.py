from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Optional
from app.repositories.market_repository import MarketRepository
from app.schemas import MarketSymbolResponse, MarketSymbolUpdate
from app.models.market import MarketSymbol
from app.models.data_source import DataSource
from fastapi import HTTPException

class MarketService:
    @staticmethod
    def get_active_broker_name(db: Session) -> Optional[str]:
        """Helper to get the active data source name."""
        active_source = db.query(DataSource).filter(DataSource.is_active == True).first()
        return active_source.name if active_source else None

    @staticmethod
    def get_active_symbols(db: Session, broker: Optional[str]) -> List[MarketSymbolResponse]:
        if not broker:
            broker = MarketService.get_active_broker_name(db)
            if not broker:
                return []

        repo = MarketRepository(db)
        symbols = repo.get_active_symbols(broker)
        # Convert to Pydantic models
        return [MarketSymbolResponse.model_validate(s) for s in symbols]

    @staticmethod
    def update_status(db: Session, symbol_id: UUID, update_data: MarketSymbolUpdate) -> MarketSymbolResponse:
        repo = MarketRepository(db)
        symbol = repo.get_by_id(symbol_id)
        if not symbol:
            raise HTTPException(status_code=404, detail="Symbol not found")
            
        updated_symbol = repo.update(symbol, is_active=update_data.is_active, details=update_data.details)
        return MarketSymbolResponse.model_validate(updated_symbol)

    @staticmethod
    def create_symbol(db: Session, broker_name: str, symbol: str) -> MarketSymbolResponse:
        repo = MarketRepository(db)
        
        # 1. Find Data Source
        ds = db.query(DataSource).filter(DataSource.name == broker_name).first()
        if not ds:
            raise HTTPException(status_code=404, detail=f"Broker '{broker_name}' not found")
            
        # 2. Check if exists
        existing = db.query(MarketSymbol).filter(
            MarketSymbol.symbol == symbol,
            MarketSymbol.data_source_id == ds.id
        ).first()
        
        if existing:
            # If exists but inactive, reactivate
            if not existing.is_active:
                repo.update_status(existing, True)
            return MarketSymbolResponse.model_validate(existing)

        # 3. Resolve Category (Default to 'Imported')
        category = repo.get_category_by_name("Imported")
        if not category:
            category = repo.create_category("Imported")
            
        # 4. Create
        new_symbol = repo.create_symbol(symbol, category.id, ds.id)
        return MarketSymbolResponse.model_validate(new_symbol)
