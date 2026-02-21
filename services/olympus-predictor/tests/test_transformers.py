import pytest
import numpy as np
import pandas as pd
from src.app.domain.transformers import LogReturnTransformer

def test_log_return_transformation():
    # Test valid prices
    prices = pd.Series([100.0, 110.0, 104.5, 115.0])
    returns = LogReturnTransformer.transform(prices)
    
    assert len(returns) == 3
    # Check first return: ln(110/100)
    expected_r1 = np.log(110/100)
    assert pytest.approx(returns.iloc[0]) == expected_r1

def test_log_return_inverse_transformation():
    last_price = 115.0
    # Future returns
    returns = np.array([0.01, -0.02, 0.015])
    
    prices = LogReturnTransformer.inverse_transform(last_price, returns)
    
    assert len(prices) == 3
    # P1 = 115 * exp(0.01)
    assert pytest.approx(prices[0]) == 115.0 * np.exp(0.01)
    # P2 = P1 * exp(-0.02) = 115 * exp(0.01 - 0.02)
    assert pytest.approx(prices[1]) == 115.0 * np.exp(-0.01)

def test_round_trip():
    original_prices = pd.Series([100.0, 110.0, 104.5, 115.0])
    returns = LogReturnTransformer.transform(original_prices)
    
    reconstructed_prices = LogReturnTransformer.inverse_transform(original_prices.iloc[0], returns.values)
    
    # reconstructed_prices should match original_prices from index 1 onwards
    np.testing.assert_allclose(reconstructed_prices, original_prices.values[1:], rtol=1e-7)
