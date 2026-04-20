import pytest
import pandas as pd
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer

def test_lfi_calculation_stable():
    analyzer = LiquidityProfileAnalyzer()
    
    # Mock data: High OI, low strike distance (Stable)
    records = [
        {'strike': 2400, 'call_oi': 1000, 'put_oi': 0, 'dte': 10, 'symbol': 'OG', 'contract_symbol': 'OGM6', 'contract_month': 'OGM6', 'underlying_price': 2390.0},
        {'strike': 2350, 'call_oi': 0, 'put_oi': 1000, 'dte': 10, 'symbol': 'OG', 'contract_symbol': 'OGM6', 'contract_month': 'OGM6', 'underlying_price': 2390.0},
    ]
    
    # S=2390 (Near 2400)
    result = analyzer.analyze_snapshot(records, current_spot_price=2390.0)
    
    regime = result['regime']
    print(f"Stable LFI: {regime.fragility_index} ({regime.fragility_alert})")
    assert regime.fragility_index < 50
    assert regime.fragility_alert in ["STABLE", "MODERATE"]

def test_lfi_calculation_fragile():
    analyzer = LiquidityProfileAnalyzer()
    
    # Mock data: Low OI but extreme Greeks (Fragile)
    records = [
        {'strike': 2400, 'call_oi': 50, 'put_oi': 49, 'dte': 1, 'symbol': 'OG', 'contract_symbol': 'OGM6', 'contract_month': 'OGM6', 'underlying_price': 2400.0},
    ]
    
    result = analyzer.analyze_snapshot(records, current_spot_price=2400.0)
    regime = result['regime']
    
    print(f"Fragile LFI: {regime.fragility_index} ({regime.fragility_alert})")
    # At very low OI, small Greeks can spike LFI because GEX is low
    assert regime.fragility_index > 10 
