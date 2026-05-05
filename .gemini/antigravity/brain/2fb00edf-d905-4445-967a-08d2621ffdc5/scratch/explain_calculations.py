import sys
import os
import asyncio
from datetime import datetime
import pandas as pd
import numpy as np

# Mocking the environment for explanation
def explain_gold_calculations():
    print("--- 1. Data Retrieval ---")
    spot_price = 4545.45 # From Redis
    futures_price = 4747.80 # From DB underlying_price
    strike_in_db = 24000.0 # From DB
    
    print(f"Current Spot (Redis): {spot_price}")
    print(f"Futures Price (DB): {futures_price}")
    print(f"Sample Strike (DB): {strike_in_db}")
    
    print("\n--- 2. Basis Calculation ---")
    basis = futures_price - spot_price
    print(f"Basis = Futures - Spot = {futures_price} - {spot_price} = {basis}")
    
    print("\n--- 3. Strike Mapping (CFD Basis) ---")
    mapped_price = strike_in_db - basis
    print(f"Mapped Price = Strike - Basis = {strike_in_db} - {basis} = {mapped_price}")
    
    print("\n--- 4. Distance Calculation (for GEX weights) ---")
    # GEX Weight = 1.0 / (1.0 + pct_distance ** 2)
    pct_distance = abs(strike_in_db - spot_price) / spot_price * 100.0
    weight = 1.0 / (1.0 + pct_distance ** 2)
    print(f"Percentage Distance = abs({strike_in_db} - {spot_price}) / {spot_price} * 100 = {pct_distance:.2f}%")
    print(f"Weighting Factor (ATM focus): {weight:.6f}")
    
    print("\n--- 5. Black-Scholes Greeks Input ---")
    print(f"S (Spot) = {spot_price}")
    print(f"K (Strike) = {mapped_price} (Calculated from DB Strike)")
    
    print("\n--- 6. Analysis Result ---")
    if pct_distance > 25:
        print("⚠️ ALERT: Distance > 25%. This strike is considered too far OTM for meaningful Gamma.")
    
    if mapped_price > spot_price * 2:
         print("⚠️ ALERT: Mapped Strike is > 2x Spot. This usually triggers DATA_INTEGRITY_ALERT.")

if __name__ == "__main__":
    explain_gold_calculations()
