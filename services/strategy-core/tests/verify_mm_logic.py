import os
import sys
import numpy as np
import time

# Mock the project structure for host execution
sys.path.append(os.path.abspath("services/strategy-core"))

from app.logic.market_maker import EFPModel

def test_mm_skew_logic():
    print("Testing EFPModel Skew Logic...")
    
    # Initialize model
    model = EFPModel(gamma=0.1)
    
    # Simulate an EFP event
    # Spot: 2700.5, Futures: 2715.2 -> Spread: 14.7
    spread = 14.7
    
    # Inventory: 0
    print(f"Applying EFP Tick: Spread={spread}")
    
    # Check if skews were generated (normally sent via execution_client)
    # Since we can't easily capture the execution_client call, 
    # we'll look at the internal model state if exposed or just run the solver manually.
    
    # Use model logic but passing parameters correctly
    # q_s=0, q_f=0, spread=14.7, d=0, t_rem=3600
    delta_b, delta_a = model.get_optimal_skews(0.0, 0.0, 14.7, 0.0, 3600.0)
    
    print(f"Optimal Skews (Inv=0): Bid={delta_b:.6f}, Ask={delta_a:.6f}")
    assert delta_b > 0 and delta_a > 0, "Skews should be positive"
    
    # Test skew with inventory
    delta_b_long, delta_a_long = model.get_optimal_skews(10.0, 0.0, 14.7, 0.0, 3600.0)
    print(f"Optimal Skews (Inv=10): Bid={delta_b_long:.6f}, Ask={delta_a_long:.6f}")
    
    assert delta_b_long < delta_b, "Bid skew should decrease with long inventory to discourage more buying"
    assert delta_a_long > delta_a, "Ask skew should increase with long inventory to encourage selling"
    
    print("MarketMakerStrategy Skew Logic Verification: SUCCESS")

if __name__ == "__main__":
    test_mm_skew_logic()
