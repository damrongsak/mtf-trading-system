import json
import logging
import asyncio
from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

logger = logging.getLogger(__name__)

class MarketDataHandler:
    """
    Handles persistence and specialized logic for market data events.
    Separates database concerns from the streaming Manager.
    """
    
    @staticmethod
    def handle_symbol_info(symbol: str, data_json: str):
        """Update MarketSymbol.details in DB with received info (ECST)."""
        try:
            data = json.loads(data_json)
            details = data.get("details")
            if not details:
                return

            db = SessionLocal()
            try:
                source_provider = data.get("source", "").upper()
                
                # Robust matching: Handle "/" vs "_" and filter by data source provider
                # We normalize the symbol comparison by trying common variations
                sym_variants = [symbol, symbol.replace("_", "/"), symbol.replace("/", "_")]
                
                query = db.query(MarketSymbol).join(DataSource).filter(
                    MarketSymbol.symbol.in_(sym_variants)
                )
                
                if source_provider:
                    query = query.filter(DataSource.provider == source_provider)
                
                ms = query.first()
                
                if ms:
                    ms.details = details
                    db.commit()
                    logger.info(f"ECST: Updated cache for {symbol} ({source_provider})")
                else:
                    logger.warning(f"ECST: Symbol {symbol} ({source_provider}) not found in DB")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Failed to update symbol cache for {symbol}: {e}")

    @staticmethod
    async def handle_symbol_info_async(symbol: str, data_json: str):
        """Asynchronous wrapper for handle_symbol_info using thread pool."""
        await asyncio.to_thread(MarketDataHandler.handle_symbol_info, symbol, data_json)
