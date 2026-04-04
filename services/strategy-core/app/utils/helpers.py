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

def resolve_market_symbol(db: Session, symbol: str, data_source: str = None, fund_id: str = None) -> 'MarketSymbol':
    """
    Resolve MarketSymbol object from symbol string with cross-service hierarchy support.
    
    Standard variants: XAUUSD, XAU_USD, XAU/USD, XAU-USD
    """
    from app.models.market import MarketSymbol
    from app.models.data_source import DataSource
    from app.models.broker_account import BrokerAccount
    
    # 1. Standardize and create variants
    clean = symbol.upper().replace("/", "").replace("_", "").replace("-", "").replace(" ", "")
    sym_variants = list(set([symbol.upper(), clean, symbol.replace("/", "_"), symbol.replace("_", "/")]))
    
    # 2. Hierarchy override: If fund_id is provided, find the linked data source
    if fund_id and not data_source:
        account = db.query(BrokerAccount).filter(
            BrokerAccount.fund_id == fund_id,
            BrokerAccount.is_active == True
        ).first()
        if account and account.data_source_id:
            # We found an authoritative source for this fund
            return db.query(MarketSymbol).filter(
                MarketSymbol.symbol.in_(sym_variants),
                MarketSymbol.data_source_id == account.data_source_id
            ).first()

    # 3. Standard resolution logic (existing)
    query = db.query(MarketSymbol).join(DataSource)
    
    if data_source:
        query = query.filter(DataSource.name == data_source)
    else:
        # Prioritize CTRADER then OANDA if source is ambiguous (institutional standard)
        ct_ms = db.query(MarketSymbol).join(DataSource).filter(
            MarketSymbol.symbol.in_(sym_variants),
            DataSource.name == "CTRADER"
        ).first()
        if ct_ms: return ct_ms
        
    return query.filter(MarketSymbol.symbol.in_(sym_variants)).first()

def resolve_market_symbol_id(db: Session, symbol: str, data_source: str = None, fund_id: str = None) -> str:
    """
    Wrapper for resolving symbol ID with fund context.
    """
    ms = resolve_market_symbol(db, symbol, data_source, fund_id)
    return str(ms.id) if ms else None
