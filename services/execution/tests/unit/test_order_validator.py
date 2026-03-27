import pytest
from app.validators.order_validator import OrderValidator
from app.models import RiskFilter

def create_filter(filter_type, params=None):
    if params is None:
        params = {}
    f = RiskFilter()
    f.filter_type = filter_type
    f.is_enabled = True
    f.threshold_parameters = params
    return f

def test_validator_sl_mandatory_missing():
    filters = [create_filter("SL_MANDATORY")]
    with pytest.raises(ValueError, match="Stop Loss is mandatory"):
        OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=0, tp_price=5300.00, side="BUY", order_type="MARKET", active_filters=filters)

def test_validator_tp_mandatory_missing():
    filters = [create_filter("TP_MANDATORY")]
    with pytest.raises(ValueError, match="Take Profit is mandatory"):
        OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=5260.00, tp_price=0, side="BUY", order_type="MARKET", active_filters=filters)

def test_validator_sl_distance_failure():
    # SL is only 5 pips away ($0.5), min is 10
    filters = [create_filter("SL_DISTANCE", {"min_pip_distance": 10.0})]
    with pytest.raises(ValueError, match="SL Distance too small"):
        OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=5279.50, tp_price=5300.00, side="BUY", order_type="LIMIT", current_ask=5281.0, active_filters=filters)

def test_validator_sl_distance_success():
    # SL is 200 pips away ($20)
    filters = [create_filter("SL_DISTANCE", {"min_pip_distance": 200.0})]
    assert OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=5260.00, tp_price=5300.00, side="BUY", order_type="LIMIT", current_ask=5281.0, active_filters=filters) == True

def test_validator_rr_ratio_failure():
    # Risk is 20, Reward is 20, RR = 1.0, min = 1.5
    filters = [create_filter("RR_RATIO", {"min_ratio": 1.5})]
    with pytest.raises(ValueError, match="RR Ratio too low"):
        OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=5260.00, tp_price=5300.00, side="BUY", order_type="MARKET", active_filters=filters)

def test_validator_rr_ratio_success():
    # Risk is 20, Reward is 40, RR = 2.0, min = 1.5
    filters = [create_filter("RR_RATIO", {"min_ratio": 1.5})]
    assert OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=5260.00, tp_price=5320.00, side="BUY", order_type="MARKET", active_filters=filters) == True

def test_disabled_filter_ignored():
    f = create_filter("SL_MANDATORY")
    f.is_enabled = False
    filters = [f]
    # Should not raise even if sl_price is missing
    assert OrderValidator.validate(symbol="XAUUSD", entry_price=5280.00, sl_price=0, tp_price=5300.00, side="BUY", order_type="MARKET", active_filters=filters) == True
