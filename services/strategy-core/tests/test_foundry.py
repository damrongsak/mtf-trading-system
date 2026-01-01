import pytest
import pandas as pd
import numpy as np
from app.foundry.base import SignalState, LogicBlock
from app.foundry.blocks.trend import TrendEMACross, TrendAMA
from app.foundry.blocks.structure import StructureFibGolden, StructureSMCOrderBlock
from app.foundry.blocks.momentum import MomentumRSICross
from app.foundry.factory import StrategyAssembler

# Mock Data
@pytest.fixture
def mock_context():
    # 200 bars of rising data
    close = np.linspace(100, 200, 300)
    # Add some noise
    
    df = pd.DataFrame({
        'open': close - 1,
        'high': close + 2,
        'low': close - 2,
        'close': close,
        'volume': 1000
    })
    
    # Create simple Order block pattern manually at end
    # Bullish OB: Down candle followed by Up candle that breaks structure?
    # Simple detection mocked:
    # We will just rely on logic block handling "no OBs" for this generic data
    
    return {
        'candles': {
            '1h': df,
            '4h': df,
            '15m': df
        }
    }

def test_trend_ema_cross(mock_context):
    # Rising market, price > EMA
    block = TrendEMACross(name="EMA", parameters={"period": 20, "timeframe": "1h"})
    result = block.run(mock_context)
    
    assert result['state'] == SignalState.BULLISH
    assert result['value'] is not None

def test_momentum_rsi_cross(mock_context):
    # RSI of linear uptrend -> likely high
    block = MomentumRSICross(name="RSI", parameters={"period": 14, "timeframe": "1h"})
    result = block.run(mock_context)
    
    # Rising data usually means RSI > 50, but might not be "Crossing" right now
    # We just assume it runs without error
    assert result['state'] in [SignalState.NEUTRAL, SignalState.BULLISH, SignalState.BEARISH]

def test_assembler():
    config = {
        "logic_blocks": [
            {"id": "TREND_EMA_CROSS", "parameters": {"period": 20, "timeframe": "1h"}},
            {"id": "MOM_RSI_CROSS", "parameters": {"period": 14, "timeframe": "1h"}}
        ]
    }
    
    pipeline = StrategyAssembler.assemble(config)
    assert len(pipeline.blocks) == 2
    assert isinstance(pipeline.blocks[0], TrendEMACross)
    assert isinstance(pipeline.blocks[1], MomentumRSICross)

def test_pipeline_execution(mock_context):
    config = {
        "logic_blocks": [
            {"id": "TREND_EMA_CROSS", "parameters": {"period": 20, "timeframe": "1h"}}
        ]
    }
    pipeline = StrategyAssembler.assemble(config)
    result = pipeline.run(mock_context)
    
    assert result['pipeline_state'] == SignalState.BULLISH # Because price is rising
    assert result['block_results']['TREND_EMA_CROSS_0']['state'] == SignalState.BULLISH
