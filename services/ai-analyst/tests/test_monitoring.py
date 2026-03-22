import pytest
import pandas as pd
import numpy as np
from app.services.monitoring import DriftMonitor

def test_kl_divergence_no_drift():
    """Verify KL Divergence is near zero for similar distributions."""
    monitor = DriftMonitor(baseline_mu=0.0, baseline_sigma=0.001)
    # Generate data with same mean and sigma
    np.random.seed(42)
    data = np.random.normal(0.0, 0.001, 200)
    returns = pd.Series(data)
    
    kl_div = monitor.calculate_kl_divergence(returns)
    assert kl_div < 0.1

def test_kl_divergence_with_drift():
    """Verify KL Divergence spikes when mean or sigma shifts."""
    monitor = DriftMonitor(baseline_mu=0.0, baseline_sigma=0.001)
    np.random.seed(42)
    
    # 1. Shift Mean significantly
    data_mean_shift = np.random.normal(0.005, 0.001, 200)
    kl_mean = monitor.calculate_kl_divergence(pd.Series(data_mean_shift))
    
    # 2. Shift Sigma significantly
    data_sigma_shift = np.random.normal(0.0, 0.005, 200)
    kl_sigma = monitor.calculate_kl_divergence(pd.Series(data_sigma_shift))
    
    assert kl_mean > 0.5
    assert kl_sigma > 0.5

def test_check_drift_trigger():
    """Verify check_drift returns correct boolean flag."""
    monitor = DriftMonitor(baseline_mu=0.0, baseline_sigma=0.001)
    monitor.drift_threshold = 0.5
    np.random.seed(42)
    
    # Normal data: Random walk with same mu/sigma
    returns_normal = np.random.normal(0.0, 0.001, 100)
    prices_normal = 100.0 * np.exp(np.cumsum(returns_normal))
    df_normal = pd.DataFrame({'close': prices_normal})
    
    res_normal = monitor.check_drift(df_normal)
    assert res_normal['is_drifted'] is False
    
    # Extreme drift (massive sell-off)
    returns_drift = np.random.normal(-0.05, 0.01, 100)
    prices_drift = 100.0 * np.exp(np.cumsum(returns_drift))
    df_drift = pd.DataFrame({'close': prices_drift})
    
    res_drift = monitor.check_drift(df_drift)
    assert res_drift['is_drifted'] is True
    assert res_drift['kl_div'] > 0.5
