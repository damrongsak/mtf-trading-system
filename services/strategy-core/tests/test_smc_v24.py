import pytest
import pandas as pd
import numpy as np
from app.logic.core import detect_choch, detect_bos_recent, calculate_confluence_score

@pytest.fixture
def sample_df():
    # Create a bullish structure
    data = {
        'high': [100, 105, 110, 108, 112, 115, 113, 118, 120, 122],
        'low': [90, 95, 100, 102, 105, 108, 106, 110, 115, 118],
        'close': [95, 100, 105, 103, 110, 113, 111, 116, 119, 121],
        'open': [92, 98, 102, 105, 107, 110, 112, 114, 117, 119]
    }
    return pd.DataFrame(data)

def test_detect_choch_logic(sample_df):
    is_choch, msg = detect_choch(sample_df, "LONG")
    assert isinstance(is_choch, bool)
    assert isinstance(msg, str)

def test_detect_bos_recent_logic(sample_df):
    has_bos = detect_bos_recent(sample_df, "LONG", lookback=5)
    assert isinstance(has_bos, bool)

def test_confluence_score_v24(sample_df):
    checklist = {}
    # Use the same df for all timeframes for simple test
    score = calculate_confluence_score(
        checklist, sample_df, sample_df, sample_df, "LONG", is_case_b=True, trigger_tf="M15"
    )
    
    assert 0 <= score <= 6
    assert "trend" in checklist
    assert "poi" in checklist
    assert "trigger" in checklist
    assert "displacement" in checklist
    assert "volatility" in checklist
    assert "risk_reward" in checklist
    
    # Check if trigger_tf is reflected in comment if possible (not explicitly in comment but logic uses it)
    print(f"Scored: {score}")
    print(f"Checklist: {checklist}")
