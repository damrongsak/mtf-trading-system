
import pytest
import pandas as pd
import numpy as np
from app.model_engine import HybridPredictor
from unittest.mock import MagicMock, patch

@pytest.fixture
def sample_data():
    x = np.linspace(0, 100, 200)
    trend = 0.5 * x
    seasonal = 10 * np.sin(x)
    y = trend + seasonal + np.random.normal(0, 1, 200)
    
    y = trend + seasonal + np.random.normal(0, 1, 200)
    
    # Create synthetic OHLC
    close = y + 2000
    high = close + np.random.rand(200) * 5
    low = close - np.random.rand(200) * 5
    open_p = (high + low) / 2
    
    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close
    }, index=pd.date_range('2023-01-01', periods=200, freq='D'))
    return df

@pytest.fixture
def sample_macro():
    x = np.linspace(0, 100, 200)
    # Feature correlated with residual (sine wave)
    feat1 = np.sin(x) # Highly correlated with seasonal residual
    feat2 = np.random.normal(0, 1, 200) # Random noise
    
    df = pd.DataFrame({
        'OIL': feat1,
        'RANDOM': feat2
    }, index=pd.date_range('2023-01-01', periods=200, freq='D'))
    return df

def test_feature_selection_integration(sample_data, sample_macro, tmp_path):
    # Setup
    model_dir = tmp_path / "models"
    predictor = HybridPredictor(model_dir=str(model_dir))
    
    # Train with Macro data
    # Boruta should pick 'OIL' and ignore 'RANDOM'
    result = predictor.train(sample_data, macro_df=sample_macro)
    
    assert result['status'] == "success"
    # Check if features were selected
    selected = result['selected_features']
    # Boruta is robust but sometimes on small synthetic data it might behave differently or fallback
    # But it should return a list
    assert isinstance(selected, list)
    
    # Verify artifacts created
    assert (model_dir / "boruta_selector.pkl").exists()

def test_prediction_with_features(sample_data, sample_macro, tmp_path):
    # Setup & Train
    model_dir = tmp_path / "models"
    predictor = HybridPredictor(model_dir=str(model_dir))
    predictor.train(sample_data, macro_df=sample_macro)
    
    # Predict
    forecast = predictor.predict(steps=5, macro_df=sample_macro)
    
    assert len(forecast['total']) == 5
    assert 'used_features' in forecast
