
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.adapters.ctrader import CTraderOrderAdapter
import uuid

@pytest.mark.asyncio
async def test_resolve_symbol_id_flexible_naming():
    # Patch where it's defined since it's imported locally in the method
    # Actually, patching app.database.AsyncSessionLocal is safer
    with patch("app.database.AsyncSessionLocal") as mock_session_factory:
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        
        # Test Case 1: Inconsistent JSON (symbolId in raw)
        mock_ms_raw = MagicMock()
        mock_ms_raw.symbol = "XAU_USD"
        mock_ms_raw.details = {"raw": {"symbolId": 41}}
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.side_effect = [None, mock_ms_raw]
        mock_db.execute.return_value = mock_result
        
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        
        # This should succeed after fix
        symbol_id = await adapter._resolve_symbol_id("XAUUSD")
        assert symbol_id == 41

        # Test Case 2: Exact Match but nested
        mock_ms_exact = MagicMock()
        mock_ms_exact.symbol = "XAU/USD"
        mock_ms_exact.details = {"symbolId": 100}
        
        mock_result_exact = MagicMock()
        mock_result_exact.scalars.return_value.first.return_value = mock_ms_exact
        mock_db.execute.return_value = mock_result_exact
        
        symbol_id = await adapter._resolve_symbol_id("XAU/USD")
        assert symbol_id == 100

@pytest.mark.asyncio
async def test_resolve_symbol_id_fails_if_not_found():
    with patch("app.database.AsyncSessionLocal") as mock_session_factory:
        mock_db = AsyncMock()
        mock_session_factory.return_value.__aenter__.return_value = mock_db
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = mock_result
        
        adapter = CTraderOrderAdapter("id", "secret", "123", "token")
        
        with pytest.raises(ValueError, match="Symbol NON_EXISTENT not found"):
            await adapter._resolve_symbol_id("NON_EXISTENT")
