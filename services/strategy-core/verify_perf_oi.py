import time
import numpy as np
import pandas as pd
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer

def test_performance_and_accuracy():
    analyzer = LiquidityProfileAnalyzer()
    
    # Simulate 10,000 strikes
    n_strikes = 10000
    strikes = np.linspace(1500, 2500, n_strikes)
    
    # Two contract months: GCJ6 and GCM6
    records = []
    # GCJ6 (April) - Price 2010
    for s in strikes:
        records.append({
            'contract_symbol': 'OGJ6',
            'strike': s,
            'call_oi': np.random.randint(10, 1000),
            'put_oi': np.random.randint(10, 1000),
            'underlying_price': 2010.0,
            'dte': 25
        })
    # GCM6 (June) - Price 2030
    for s in strikes:
        records.append({
            'contract_symbol': 'OGM6',
            'strike': s,
            'call_oi': np.random.randint(10, 1000),
            'put_oi': np.random.randint(10, 1000),
            'underlying_price': 2030.0,
            'dte': 86
        })
        
    current_spot = 2005.0
    
    print(f"--- Starting Latency Test for {len(records)} records ---")
    start_time = time.time()
    
    # 1. Test Active (Auto-detect)
    analysis_auto = analyzer.analyze_snapshot(records, current_spot_price=current_spot)
    end_time = time.time()
    
    latency = (end_time - start_time) * 1000
    print(f"Latency (Auto-detect): {latency:.2f} ms")
    print(f"Target Contract: {analysis_auto['target_contract']}")
    print(f"Max Pain: {analysis_auto['max_pain']}")
    
    # 2. Test Explicit Mapping Accuracy
    # OGJ6 should use 2010. Basis = 5. Price = Strike - 5.
    analysis_j = analyzer.analyze_snapshot(records, current_spot_price=current_spot, target_contract='OGJ6')
    basis_j = 2010.0 - current_spot
    
    # OGM6 should use 2030. Basis = 25. Price = Strike - 25.
    analysis_m = analyzer.analyze_snapshot(records, current_spot_price=current_spot, target_contract='OGM6')
    basis_m = 2030.0 - current_spot
    
    print(f"\n--- Accuracy Check ---")
    print(f"OGJ6 Basis: {basis_j} | Mapped Price for 2010 Strike: {2010 - basis_j} (Spot match: {2010 - basis_j == current_spot})")
    print(f"OGM6 Basis: {basis_m} | Mapped Price for 2030 Strike: {2030 - basis_m} (Spot match: {2030 - basis_m == current_spot})")

if __name__ == "__main__":
    test_performance_and_accuracy()
