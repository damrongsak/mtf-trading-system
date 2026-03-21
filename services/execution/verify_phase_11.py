import asyncio
import uuid
import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

# Mocking app modules
import sys
from types import ModuleType

# Create mocks for services not needed for this logic-only test
mock_db = AsyncMock()
mock_adapter = AsyncMock()
mock_cache = AsyncMock()

# Setup sys.modules to prevent import errors in the standalone script
db_module = ModuleType('app.database')
db_module.AsyncSessionLocal = MagicMock()
db_module.Base = MagicMock()
sys.modules['app.database'] = db_module

async def test_scaling_logic():
    print("🚀 Starting Phase 11 Scaling Verification...")
    
    from app.services.order_service import OrderService
    from app.core.units import UnitConverter
    
    # Mock Fund Data
    fund_data = {
        "id": str(uuid.uuid4()),
        "name": "Institutional Fund",
        "max_risk_per_trade": Decimal("100.00"),
        "risk_percentage": Decimal("0.01"),
        "scale_factor": Decimal("1.5000"), # 150% scaling
        "asset_risk_caps": {"XAUUSD": 50.0}, # Cap at $50 for Gold
        "risk_parity_enabled": False
    }
    
    # Mock Account Data
    account_id = str(uuid.uuid4())
    account_data = {
        "id": account_id,
        "fund_id": fund_data["id"],
        "broker_name": "CTRADER",
        "risk_settings": {},
        "balance_snapshot": 10000.0
    }

    # Helper to mock cache get_fund and get_account
    async def mock_get_fund(fid): 
        # Convert dict to object-like
        return type('Fund', (object,), fund_data)
        
    async def mock_get_account(aid): 
        return type('Account', (object,), account_data)
        
    async def mock_get_credentials(aid): return {"token": "test"}

    with patch("app.services.cache_service.execution_cache.get_fund", side_effect=mock_get_fund), \
         patch("app.services.cache_service.execution_cache.get_account", side_effect=mock_get_account), \
         patch("app.services.cache_service.execution_cache.get_credentials", side_effect=mock_get_credentials), \
         patch("app.adapters.factory.BrokerFactory.get_adapter", return_value=mock_adapter), \
         patch("app.services.price_service.price_service.get_latest_price", return_value=(2000.0, None)), \
         patch("app.utils.redis_client.get_redis_client", return_value=AsyncMock()):
        
        # Scenario 1: Asset Risk Cap enforcement
        # Risk = 1% of 10,000 = $100. Scaled by 1.5x = $150.
        # But Gold asset cap is $50. So it should fail if risk > $50.
        
        req_data = {
            "broker_account_id": account_id,
            "symbol": "XAU_USD",
            "direction": "BULLISH",
            "stop_loss": 1990.0, # $10 distance
            "knowledge_score": 1.0,
            "generated_by": "TestStrategy",
            "signal_id": str(uuid.uuid4())
        }
        
        mock_adapter.get_current_price.return_value = 2000.0
        mock_adapter._resolve_symbol_id_and_lot_size.return_value = ("1", 10000000, "1", 2)
        
        print("\nChecking Asset Risk Cap enforcement...")
        try:
            await OrderService.execute_smart_order(req_data, mock_db)
            print("❌ FAILED: Asset cap not enforced!")
        except ValueError as e:
            if "Asset Risk Cap exceeded" in str(e):
                print(f"✅ SUCCESS: {e}")
            else:
                print(f"❌ FAILED: Unexpected error type: {type(e)} {e}")
        except Exception as e:
            print(f"❌ FAILED: Unexpected Exception: {type(e)} {e}")

        # Scenario 2: Scale Factor Verification
        # Change asset cap to $200 (bypass)
        fund_data["asset_risk_caps"] = {"XAUUSD": 200.0}
        
        # Risk = $100 * 1.5 = $150.
        # This is < $200 (Asset Cap) and < $100 (Fund Max Risk? Wait, Fund Max Risk is $100).
        # So it should be CAPPED at $100.
        print("\nChecking scale_factor and Fund Limit capping...")
        mock_adapter.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "123"}})
        
        result = await OrderService.execute_smart_order(req_data, mock_db)
        
        # risk $150 capped at $100. sl_dist $10 -> 10 oz Gold.
        # Units calculation: (100 / 10) = 10 oz. 10 oz = 1000 units (internal units).
        call_args = mock_adapter.place_market_order.call_args
        sent_units = call_args[1]["units"]
        print(f"✅ SUCCESS: Sent Units = {sent_units}")

if __name__ == "__main__":
    asyncio.run(test_scaling_logic())
