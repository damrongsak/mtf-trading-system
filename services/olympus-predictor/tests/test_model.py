import pytest
import pandas as pd
import numpy as np
from src.app.domain.models import HybridPredictor
from src.app.domain.transformers import LogReturnTransformer
from unittest.mock import MagicMock, patch

@pytest.fixture
def sample_data():
    # Create fake price series that is trending up
    dates = pd.date_range('2023-01-01', periods=300, freq='15min')
    x = np.linspace(0, 1, 300)
    close = 2000 + 100 * x + 5 * np.sin(20 * x) + np.random.normal(0, 1, 300)
    high = close + 2
    low = close - 2
    open_p = close + 0.5
    
    df = pd.DataFrame({
        'open': open_p,
        'high': high,
        'low': low,
        'close': close,
        'volume': 1000 * np.random.rand(300)
    }, index=dates)
    return df

@pytest.fixture
def sample_macro(sample_data):
    df = pd.DataFrame({
        'OIL': 70 + 5 * np.sin(np.linspace(0, 1, 300)),
        'RANDOM': np.random.normal(0, 1, 300)
    }, index=sample_data.index)
    return df

def test_full_hybrid_pipeline(sample_data, sample_macro, tmp_path):
    model_dir = tmp_path / "models"
    predictor = HybridPredictor(model_dir=str(model_dir))
    
    # Train
    train_res = predictor.train(sample_data, macro_df=sample_macro)
    assert train_res['status'] == "success"
    
    # Predict
    last_price = sample_data['close'].iloc[-1]
    pred_res = predictor.predict(steps=5, macro_df=sample_macro, last_price=last_price)
    
    assert len(pred_res['prices']) == 5
    assert len(pred_res['sigma_lr']) == 5
    assert pred_res['prices'][0] > 0
    assert 'total_lr' in pred_res
