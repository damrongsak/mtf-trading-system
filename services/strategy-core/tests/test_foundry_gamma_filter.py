import pytest
import pandas as pd
from app.foundry.base import SignalState
from app.foundry.blocks.filters import FilterGammaRegime
from app.foundry.factory import StrategyPipeline

def test_gamma_filter_pass():
    filter_block = FilterGammaRegime("gamma", {"regime": "NEGATIVE_GAMMA"})
    pipeline = StrategyPipeline([filter_block])
    
    context = {"analytics": {"gamma_regime": "NEGATIVE_GAMMA"}}
    result = pipeline.run(context)
    
    assert result['pipeline_state'] == SignalState.NEUTRAL
    assert result['block_results']['gamma']['state'] == SignalState.NEUTRAL

def test_gamma_filter_veto():
    filter_block = FilterGammaRegime("gamma", {"regime": "NEGATIVE_GAMMA"})
    pipeline = StrategyPipeline([filter_block])
    
    context = {"analytics": {"gamma_regime": "POSITIVE_GAMMA"}}
    result = pipeline.run(context)
    
    assert result['pipeline_state'] == SignalState.INVALID
    assert result['block_results']['gamma']['state'] == SignalState.INVALID

def test_gamma_filter_strict_no_data():
    filter_block = FilterGammaRegime("gamma", {"regime": "NEGATIVE_GAMMA", "strict": True})
    pipeline = StrategyPipeline([filter_block])
    
    context = {"analytics": {}}
    result = pipeline.run(context)
    
    assert result['pipeline_state'] == SignalState.INVALID
    assert result['block_results']['gamma']['state'] == SignalState.INVALID

def test_gamma_filter_vector():
    filter_block = FilterGammaRegime("gamma", {"regime": "NEGATIVE_GAMMA"})
    
    context = {
        "analytics": {
            "gamma_regime": pd.Series(["POSITIVE_GAMMA", "NEGATIVE_GAMMA", "NEGATIVE_GAMMA"])
        }
    }
    
    result = filter_block.run_vector(context)
    # Expect 0 (fail), 1 (pass), 1 (pass)
    assert result.iloc[0] == 0
    assert result.iloc[1] == 1
    assert result.iloc[2] == 1
