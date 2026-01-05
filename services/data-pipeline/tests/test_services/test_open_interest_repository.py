import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from app.repositories.open_interest_repository import OpenInterestRepository
from app.models.open_interest import OpenInterest

# Mock Row object to simulate SQLAlchemy result
class MockRow:
    def __init__(self, strike, total_oi, total_call_oi=0, total_put_oi=0):
        self.strike = strike
        self.total_oi = total_oi
        self.total_call_oi = total_call_oi
        self.total_put_oi = total_put_oi

def test_get_active_strike_range_calculation():
    """
    Test the Weighted Mean and StdDev calculation for Smart Filter.
    Scenario:
    - Strikes: 2000, 2010, 2020
    - OIs:     100,  1000, 100 
    - Mean should be exactly 2010.
    - Variance/StdDev will be small.
    - Expected Range: around 2010 +/- (2 * std_dev)
    """
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_db.execute = mock_execute
    
    # Mock return rows
    rows = [
        MockRow(strike=2000, total_oi=100),
        MockRow(strike=2010, total_oi=1000),
        MockRow(strike=2020, total_oi=100)
    ]
    
    mock_result = MagicMock()
    mock_result.fetchall.return_value = rows
    mock_execute.return_value = mock_result
    
    repo = OpenInterestRepository(mock_db)
    snapshot_at = datetime.now()
    
    min_k, max_k = repo.get_active_strike_range(snapshot_at, std_dev_multiplier=2.0)
    
    # Validation
    # Mean should be 2010
    # Variance approx: (100*(10^2) + 100*(10^2)) / 1200 = 20000 / 1200 = 16.66
    # StdDev = 4.08
    # Range = 2010 +/- 8.16 => [2001.8, 2018.1]
    # But wait, logic: 
    # Mean = ((2000*100) + (2010*1000) + (2020*100)) / 1200
    #      = (200000 + 2010000 + 202000) / 1200
    #      = 2412000 / 1200 = 2010. Correct.
    
    assert min_k < 2010
    assert max_k > 2010
    
    # Ensure it's not the full range (2000-2020) if multiplier is tight enough
    # With mult=2.0 and std_dev~4, range is ~2002 to 2018
    assert min_k > 2000
    assert max_k < 2020

def test_get_analysis_data_smart_filter():
    """
    Test that get_analysis_data calls get_active_strike_range when smart_filter=True.
    """
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_db.execute = mock_execute
    
    # Setup calculation rows (Test 1 logic)
    calc_rows = [
        MockRow(strike=2000, total_oi=100),
        MockRow(strike=2010, total_oi=1000),
        MockRow(strike=2020, total_oi=100)
    ]
    # Setup final query rows (filtered)
    final_rows = [
        MockRow(strike=2010, total_oi=1000, total_call_oi=500, total_put_oi=500)
    ]
    
    # We expect 2 execute calls:
    # 1. Calculation query
    # 2. Main query
    
    mock_result_calc = MagicMock()
    mock_result_calc.fetchall.return_value = calc_rows
    
    mock_result_final = MagicMock()
    mock_result_final.fetchall.return_value = final_rows
    
    mock_execute.side_effect = [mock_result_calc, mock_result_final]
    
    repo = OpenInterestRepository(mock_db)
    snapshot_at = datetime.now()
    
    result = repo.get_analysis_data(snapshot_at, smart_filter=True)
    
    assert result['summary']['total_call_oi'] == 500
    assert len(result['distribution']) == 1
    assert result['distribution'][0]['strike'] == 2010
    
    # Verify execute was called twice
    assert mock_execute.call_count == 2
