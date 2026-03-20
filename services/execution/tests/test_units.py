import pytest
from app.core.units import UnitConverter

def test_internal_to_ctrader_volume_gold():
    # 1 lot = 100,000 units (internal)
    # 1 lot = 10,000 cents (cTrader Gold)
    # Expected: 1,000 units (1 oz) -> 100 cents
    lot_size_cents = 10000.0
    units = 1000.0
    volume = UnitConverter.internal_to_ctrader_volume(units, lot_size_cents)
    assert volume == 100

def test_internal_to_ctrader_volume_forex():
    # 1 lot = 100,000 units (internal)
    # 1 lot = 10,000,000 cents (cTrader Forex)
    # Expected: 1,000 units (0.01 lot) -> 100,000 cents
    lot_size_cents = 10000000.0
    units = 1000.0
    volume = UnitConverter.internal_to_ctrader_volume(units, lot_size_cents)
    assert volume == 100000

def test_calculate_risk_usd_gold():
    # Price diff: 25.36 (from 4649 to 4623.64)
    # Volume: 3950 cents (from 39.5 units * 100) -> 39.5 oz
    # Expected Risk: 25.36 * 39.5 = 1001.72 (Wait, my units logic)
    # Standard Rule: Risk = price_diff * (volume / 100)
    price_diff = 25.36
    volume_cents = 3950.0
    risk = UnitConverter.calculate_risk_usd(price_diff, volume_cents)
    assert risk == 1001.72

def test_calculate_risk_usd_forex():
    # Price diff: 0.0001 (10 pips)
    # Volume: 1,000,000 cents (10,000 units = 0.1 lot)
    # Expected Risk: 0.0001 * (1,000,000 / 100) = 0.0001 * 10,000 = 1.0 USD
    price_diff = 0.0001
    volume_cents = 1000000.0
    risk = UnitConverter.calculate_risk_usd(price_diff, volume_cents)
    assert risk == 1.0

def test_step_rounding():
    # units = 39.5 -> raw_volume = 39.5 (for gold lot_size=10000)
    # step_cents = 100
    # Expected: rounded down to 0? No, min 100.
    lot_size_cents = 10000.0
    units = 39.5
    step_cents = 100.0
    volume = UnitConverter.internal_to_ctrader_volume(units, lot_size_cents, step_cents)
    assert volume == 100
