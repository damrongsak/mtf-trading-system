import pytest
import pandas as pd
import numpy as np
from app.analysis import metrics

def test_calculate_var():
    # Symmetric normal returns
    returns = pd.Series(np.random.normal(0, 0.01, 1000))
    var_95 = metrics.calculate_var(returns, 0.95)
    # 95th percentile should be around -1.645 * std
    expected_approx = -1.645 * 0.01
    assert var_95 < 0
    assert abs(var_95 - expected_approx) < 0.005

def test_calculate_cvar():
    returns = pd.Series([-0.10, -0.05, -0.02, 0.01, 0.05])
    # VaR 80% (bottom 20%) -> 1st percentile of 5 is index 0 -> -0.10
    # CVaR 80% is the mean of everything <= -0.10 -> -0.10
    cvar_80 = metrics.calculate_cvar(returns, 0.80)
    assert cvar_80 <= metrics.calculate_var(returns, 0.80)

def test_calculate_rolling_vol():
    returns = pd.Series([0.01] * 10 + [0.05] * 10)
    vol = metrics.calculate_rolling_vol(returns, window=5)
    assert len(vol) == 20
    assert pd.isna(vol.iloc[0])
    assert vol.iloc[-1] == pytest.approx(0.0) # all 0.05
    
def test_calculate_parkinson_vol():
    high = pd.Series([100, 102, 101, 103] * 5)
    low = pd.Series([98, 99, 97, 100] * 5)
    vol = metrics.calculate_parkinson_vol(high, low, window=10)
    assert vol > 0
    assert isinstance(vol, float)

def test_calculate_rolling_beta():
    returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 20)
    benchmark = returns * 0.5 # beta should be 2.0 or 0.5? 
    # Beta = Cov(R, B) / Var(B) -> if R = 2*B, Beta=2
    # Here R = 2 * (returns * 0.5) -> Beta = 1.0 if benchmark is same
    # Wait, if benchmark = returns * 0.5, then returns = 2 * benchmark. Beta should be 2.0.
    beta = metrics.calculate_rolling_beta(returns, benchmark, window=20)
    assert beta.iloc[-1] == pytest.approx(2.0)

def test_calculate_rolling_momentum():
    returns = pd.Series([0.01] * 10) # 1% each step
    # 1.01 ^ 5 - 1 approx 0.051
    mom = metrics.calculate_rolling_momentum(returns, window=5)
    assert mom.iloc[-1] == pytest.approx((1.01**5) - 1)
