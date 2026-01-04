from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

class MarketRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_symbols(self, broker: str) -> List[MarketSymbol]:
        return self.db.query(MarketSymbol).join(DataSource).filter(
            DataSource.name == broker,
            MarketSymbol.is_active == True
        ).order_by(MarketSymbol.symbol).all()

    def get_by_id(self, symbol_id: UUID) -> Optional[MarketSymbol]:
        return self.db.query(MarketSymbol).filter(MarketSymbol.id == symbol_id).first()
        
    def get_any_by_symbol(self, symbol: str) -> Optional[MarketSymbol]:
        """Get symbol by name (any broker)."""
        return self.db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol).first()

    def update_status(self, symbol: MarketSymbol, is_active: bool) -> MarketSymbol:
        symbol.is_active = is_active
        self.db.commit()
        self.db.refresh(symbol)
        return symbol

    def get_active_data_sources(self) -> List[DataSource]:
        return self.db.query(DataSource).filter(DataSource.is_active == True).all()

    def get_symbols_for_datasource(self, datasource_id: UUID) -> List[MarketSymbol]:
        return self.db.query(MarketSymbol).filter(
            MarketSymbol.data_source_id == datasource_id,
            MarketSymbol.is_active == True
        ).all()
