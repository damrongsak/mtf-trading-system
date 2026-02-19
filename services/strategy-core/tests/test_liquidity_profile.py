import pytest
import pandas as pd
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer

def test_max_pain_calculation():
    analyzer = LiquidityProfileAnalyzer()
    
    # Sample data where Max Pain should be 2000
    # If price is 2000: 
    # Loss at 1900: Call Loss = (2000-1900)*10 = 1000
    # Loss at 2100: Put Loss = (2100-2000)*10 = 1000
    # Total loss at 2000 = 0 (perfect pin)
    records = [
        {'strike': 1900, 'call_oi': 100, 'put_oi': 0, 'underlying_price': 2000},
        {'strike': 2000, 'call_oi': 1, 'put_oi': 1, 'underlying_price': 2000},
        {'strike': 2100, 'call_oi': 0, 'put_oi': 100, 'underlying_price': 2000}
    ]
    
    df = pd.DataFrame(records)
    max_pain = analyzer.calculate_max_pain(df)
    
    assert max_pain == 2000.0

def test_analyze_snapshot_integration():
    analyzer = LiquidityProfileAnalyzer()
    records = [
        {'strike': 1900, 'call_oi': 10, 'put_oi': 500, 'underlying_price': 2000},
        {'strike': 2000, 'call_oi': 100, 'put_oi': 100, 'underlying_price': 2000},
        {'strike': 2100, 'call_oi': 500, 'put_oi': 10, 'underlying_price': 2000}
    ]
    
    result = analyzer.analyze_snapshot(records, current_spot_price=2000)
    
    assert 'max_pain' in result
    assert result['max_pain'] == 2000.0
    assert 'heatmap' in result
    assert len(result['heatmap']) == 3
    
    # Check if MAX_PAIN level is in levels
    level_types = [l.type for l in result['levels']]
    assert 'MAX_PAIN' in level_types
