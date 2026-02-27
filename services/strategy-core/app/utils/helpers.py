from __future__ import annotations
import math
from typing import Any
from sqlalchemy.orm import Session

def sanitize_numeric_dict(obj: Any) -> Any:
    """
    Recursively replaces NaN and Inf with None for JSON compliance.
    """
    if isinstance(obj, dict):
        return {k: sanitize_numeric_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_numeric_dict(x) for x in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj

def resolve_market_symbol(db: Session, symbol: str, data_source: str = None) -> 'MarketSymbol':
    """
    Resolve MarketSymbol object from symbol string.
    Prioritizes CTRADER if no source is specified.
    """
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    
    sym_variants = [symbol, symbol.replace("/", "_"), symbol.replace("_", "/")]
    
    query = db.query(MarketSymbol).join(DataSource)
    
    if data_source:
        query = query.filter(DataSource.name == data_source)
    else:
        # Prioritize CTRADER then OANDA if source is ambiguous
        query = query.filter(MarketSymbol.symbol.in_(sym_variants))
        # Custom ordering to pick CTRADER first if available
        # This is a bit tricky with SQLAlchemy query.first(), so we can just pick the first one 
        # but in a real env we might order by DataSource.name.
        ms = query.order_by(DataSource.name.desc()).first() # "OANDA" < "CTRADER" but "CTRADER" comes first if we desc? No.
        # "CTRADER" vs "OANDA" -> C comes before O. 
        # Let's just try to find CTRADER explicitly first if source is None
        ct_ms = db.query(MarketSymbol).join(DataSource).filter(
            MarketSymbol.symbol.in_(sym_variants),
            DataSource.name == "CTRADER"
        ).first()
        if ct_ms: return ct_ms
        
    return query.filter(MarketSymbol.symbol.in_(sym_variants)).first()

def resolve_market_symbol_id(db: Session, symbol: str, data_source: str = "OANDA") -> str:
    """
    Legacy wrapper for resolving symbol ID.
    """
    ms = resolve_market_symbol(db, symbol, data_source)
    return str(ms.id) if ms else None
