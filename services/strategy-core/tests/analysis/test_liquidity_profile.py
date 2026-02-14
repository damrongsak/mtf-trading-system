import pytest
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer

class TestLiquidityProfileAnalyzer:
    def test_analyze_snapshot_basic(self):
        analyzer = LiquidityProfileAnalyzer()
        
        # Mock Data
        records = [
            {'strike': 2000, 'call_oi': 100, 'put_oi': 500, 'underlying_price': 2010},
            {'strike': 2050, 'call_oi': 1000, 'put_oi': 200, 'underlying_price': 2010},
            {'strike': 2100, 'call_oi': 500, 'put_oi': 100, 'underlying_price': 2010}
        ]
        
        result = analyzer.analyze_snapshot(records, current_spot_price=2005)
        
        assert 'levels' in result
        assert 'regime' in result
        
        levels = result['levels']
        # Expect Call Wall at 2050
        call_wall = next((l for l in levels if l.type == 'CALL_WALL'), None)
        assert call_wall is not None
        assert call_wall.price == 2050
        
        # Expect Put Wall at 2000
        put_wall = next((l for l in levels if l.type == 'PUT_WALL'), None)
        assert put_wall is not None
        assert put_wall.price == 2000
        
    def test_gamma_flip_positive(self):
        analyzer = LiquidityProfileAnalyzer()
        # Create a scenario where low strikes are Put heavy, high strikes are Call heavy
        records = [
            {'strike': 2000, 'call_oi': 100, 'put_oi': 1000, 'underlying_price': 2050},
            {'strike': 2050, 'call_oi': 500, 'put_oi': 500, 'underlying_price': 2050}, # Flip
            {'strike': 2100, 'call_oi': 1000, 'put_oi': 100, 'underlying_price': 2050}
        ]
        
        result = analyzer.analyze_snapshot(records, current_spot_price=2060)
        
        # Price 2060 > Flip 2050 -> Positive Gamma
        assert result['regime'].regime == 'POSITIVE_GAMMA'
        
    def test_gamma_flip_negative(self):
        analyzer = LiquidityProfileAnalyzer()
        records = [
            {'strike': 2000, 'call_oi': 100, 'put_oi': 1000, 'underlying_price': 2050},
            {'strike': 2050, 'call_oi': 500, 'put_oi': 500, 'underlying_price': 2050}, # Flip
            {'strike': 2100, 'call_oi': 1000, 'put_oi': 100, 'underlying_price': 2050}
        ]
        
        result = analyzer.analyze_snapshot(records, current_spot_price=2040)
        
        # Price 2040 < Flip 2050 -> Negative Gamma
        assert result['regime'].regime == 'NEGATIVE_GAMMA'
