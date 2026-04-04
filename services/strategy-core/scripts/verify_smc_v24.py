import pandas as pd
import numpy as np
import json
from app.logic.core import detect_choch, detect_bos_recent, calculate_confluence_score

def run_verification():
    print("--- SMC v2.4+ Institutional Logic Verification ---")
    
    # Bullish structure data
    # We simulate a swing high at index 2 (110) being broken at index 4 (112)
    data = {
        'high': [100, 105, 110, 108, 112, 115, 113, 118, 120, 122],
        'low': [90, 95, 100, 102, 105, 108, 106, 110, 115, 118],
        'close': [95, 100, 105, 103, 110, 113, 111, 116, 119, 121],
        'open': [92, 98, 102, 105, 107, 110, 112, 114, 117, 119]
    }
    df = pd.DataFrame(data)
    
    print("\n1. Testing CHoCH Detection (Bullish):")
    is_choch, msg = detect_choch(df, "LONG")
    print(f"Result: {is_choch}, Message: {msg}")
    
    print("\n2. Testing Recent BOS Detection:")
    has_bos = detect_bos_recent(df, "LONG", lookback=5)
    print(f"Result: {has_bos}")
    
    print("\n3. Testing Confluence Scoring (Flexible MTF):")
    checklist = {}
    # Use the same df for all timeframes for simple test
    score = calculate_confluence_score(
        checklist, df, df, df, "LONG", is_case_b=True, trigger_tf="M15"
    )
    print(f"Final Score: {score}/6")
    print("Checklist Details:")
    print(json.dumps(checklist, indent=2))

if __name__ == "__main__":
    run_verification()
