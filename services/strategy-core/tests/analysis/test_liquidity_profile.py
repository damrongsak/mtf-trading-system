import pytest
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer

class TestLiquidityProfileAnalyzer:
    def test_analyze_snapshot_basic(self):
        analyzer = LiquidityProfileAnalyzer()
        
        # Mock Data (Futures strikes)
        records = [
            {'strike': 2000, 'call_oi': 100, 'put_oi': 500, 'underlying_price': 2010, 'dte': 5, 'contract_symbol': 'XAUUSD'},
            {'strike': 2050, 'call_oi': 1000, 'put_oi': 200, 'underlying_price': 2010, 'dte': 5, 'contract_symbol': 'XAUUSD'},
            {'strike': 2100, 'call_oi': 500, 'put_oi': 100, 'underlying_price': 2010, 'dte': 5, 'contract_symbol': 'XAUUSD'}
        ]
        
        # basis = 2010 (Futures) - 2005 (Spot) = 5.0
        result = analyzer.analyze_snapshot(records, current_spot_price=2005)
        
        assert 'levels' in result
        assert 'regime' in result
        
        levels = result['levels']
        # Expect Call Wall at 2050 -> Spot 2045
        call_wall = next((l for l in levels if l.type == 'CALL_WALL'), None)
        assert call_wall is not None
        assert call_wall.price == 2045.0
        assert call_wall.strike == 2050.0
        assert call_wall.zone_type == 'MAJOR'
        assert call_wall.dte == 5
        
        # Expect Put Wall at 2000 -> Spot 1995
        put_wall = next((l for l in levels if l.type == 'PUT_WALL'), None)
        assert put_wall is not None
        assert put_wall.price == 1995.0
        assert put_wall.zone_type == 'MAJOR'
        
    def test_analyze_with_smc_confluence(self):
        analyzer = LiquidityProfileAnalyzer()
        records = [
            {'strike': 2050, 'call_oi': 1000, 'put_oi': 100, 'underlying_price': 2050, 'contract_symbol': 'XAUUSD'}
        ]
        
        # Mock SMC data
        smc_data = {
            'order_blocks': [{'type': 'bearish', 'top': 2055, 'bottom': 2048}],
            'auto_fibs': {'0.618': 2051}
        }
        
        # No basis (Futures = Spot = 2050)
        result = analyzer.analyze_snapshot(records, current_spot_price=2050, smc_data=smc_data)
        
        level = result['levels'][0]
        assert 'OB_BEARISH' in level.confluence
        assert 'FIB_0.618' in level.confluence
