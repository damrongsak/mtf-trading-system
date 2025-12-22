from sqlalchemy.orm import Session
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

def resolve_market_symbol_id(db: Session, symbol: str, data_source: str = "OANDA") -> str:
    """
    Resolve market_symbol_id from symbol string and data source name.
    Returns UUID string or None.
    """
    # Flexible matching: try as-is, then underscore
    target_symbol = symbol
    normalized_symbol = symbol.replace("/", "_")
    
    query = db.query(MarketSymbol).join(DataSource).filter(
        (MarketSymbol.symbol == target_symbol) | (MarketSymbol.symbol == normalized_symbol),
        DataSource.name == data_source
    )
    ms = query.first()
    return str(ms.id) if ms else None
