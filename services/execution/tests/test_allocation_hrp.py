import pytest
import pandas as pd
from app.services.allocation_service import AllocationService

@pytest.mark.asyncio
async def test_hrp_allocation_calculation():
    """
    Unit test for HRP allocation using provided price data.
    """
    # 1. Setup Mock Historical Data (Close prices for 3 symbols)
    symbols = ["XAU_USD", "EUR_USD", "BTC_USD"]
    dates = pd.date_range(start="2023-01-01", periods=10, freq="D")
    
    data = {
        "XAU_USD": [1800, 1810, 1805, 1820, 1815, 1830, 1825, 1840, 1835, 1850],
        "EUR_USD": [1.05, 1.06, 1.05, 1.07, 1.06, 1.08, 1.07, 1.09, 1.08, 1.10],
        "BTC_USD": [20000, 21000, 20500, 22000, 21500, 23000, 22500, 24000, 23500, 25000]
    }
    df = pd.DataFrame(data, index=dates)
    
    # 2. Initialize AllocationService with data
    total_equity = 10000.0
    alloc_service = AllocationService(df, total_equity)
    
    # 3. Calculate Allocation for XAU_USD
    target_units = alloc_service.calculate_allocation(symbol="XAU_USD", model="HRP")
    
    # Verify
    assert target_units > 0
    print(f"✅ HRP Target Units for XAU_USD: {target_units}")

@pytest.mark.asyncio
async def test_min_vol_allocation():
    """
    Unit test for MIN_VOL allocation.
    """
    dates = pd.date_range(start="2023-01-01", periods=5, freq="D")
    data = {
        "XAU_USD": [100, 101, 100, 102, 101], # Low vol
        "BTC_USD": [100, 150, 80, 200, 50]    # High vol
    }
    df = pd.DataFrame(data, index=dates)
    
    total_equity = 10000.0
    alloc_service = AllocationService(df, total_equity)
    
    # MIN_VOL weights
    weights = alloc_service.get_risk_parity_weights(model="MIN_VOL")
    
    assert "XAU_USD" in weights
    assert "BTC_USD" in weights
    # XAU_USD is less volatile, so it should get a higher weight in MIN_VOL
    assert weights["XAU_USD"] > weights["BTC_USD"]
    print(f"✅ Min Vol Weights: {weights}")
