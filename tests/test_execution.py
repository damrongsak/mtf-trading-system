import pytest
from decimal import Decimal
import sys
import os

# Add services to path so we can import execution app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.execution.app.executor import can_execute, ExecutionRequest

def test_can_execute_valid():
    """Test valid execution scenario (SDD Example)."""
    # Given risk_usd=10, sl_distance_usd=50, min_lot=0.01
    req = ExecutionRequest(
        risk_usd=Decimal("10.00"), 
        sl_distance_usd=Decimal("50.00"), 
        min_lot=Decimal("0.01")
    )
    res = can_execute(req)
    
    # When called, returns {can_execute:true, lot:0.2, reason:"ok"}
    assert res.can_execute is True
    assert res.lot == Decimal("0.20")
    assert res.reason == "ok"

def test_can_execute_min_lot_violation():
    """Test rejection when calculated lot is below min_lot."""
    # Risk $1, SL distance $200 => Lot 0.005 -> 0.00
    req = ExecutionRequest(
        risk_usd=Decimal("1.00"), 
        sl_distance_usd=Decimal("200.00"), 
        min_lot=Decimal("0.01")
    )
    res = can_execute(req)
    
    assert res.can_execute is False
    assert res.lot < Decimal("0.01")
    assert "below minimum" in res.reason

def test_can_execute_rounding_down():
    """Test that lot size is rounded down to avoid exceeding risk."""
    # Risk $10, SL distance $33 => 0.30303... -> Should be 0.30
    req = ExecutionRequest(
        risk_usd=Decimal("10.00"), 
        sl_distance_usd=Decimal("33.00"), 
        min_lot=Decimal("0.01")
    )
    res = can_execute(req)
    
    assert res.can_execute is True
    assert res.lot == Decimal("0.30")
    # 0.30 * 33 = 9.90 <= 10.00
    # 0.31 * 33 = 10.23 > 10.00 (Violation)

def test_can_execute_zero_sl():
    """Test handling of zero/negative SL distance."""
    req = ExecutionRequest(
        risk_usd=Decimal("10.00"), 
        sl_distance_usd=Decimal("0.00"), 
        min_lot=Decimal("0.01")
    )
    res = can_execute(req)
    
    assert res.can_execute is False
    assert "positive" in res.reason
