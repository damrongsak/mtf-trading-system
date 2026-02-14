import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class GammaLevel:
    price: float      # Mapped CFD/Spot Price
    strike: float     # Raw CME Strike Price
    type: str         # 'CALL_WALL' | 'PUT_WALL' | 'GAMMA_FLIP' | 'LEVEL'
    zone_type: str    # 'MAJOR' | 'MINOR'
    strength: float   # OI or GEX value
    description: str
    dte: Optional[int] = None # Days to Expiration
    confluence: List[str] = field(default_factory=list) # SMC/Fib confluence tags

@dataclass
class MarketRegime:
    net_gex: float
    regime: str  # 'POSITIVE_GAMMA' (Mean Reversion) or 'NEGATIVE_GAMMA' (Volatile/Trend)
    gamma_flip_level: Optional[float]
    summary: str

class LiquidityProfileAnalyzer:
    """
    Analyzes Open Interest (OI) data to identify institutional positioning,
    Gamma Walls, and Market Regimes (GEX).
    """

    def __init__(self):
        pass

    def analyze_snapshot(self, records: List[Dict[str, Any]], current_spot_price: float, smc_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a list of OI records to determine levels and regime.
        
        Args:
            records: List of dicts with keys: strike, call_oi, put_oi, underlying_price (at snapshot)
            current_spot_price: Current live price of the asset (CFD/Spot)
            smc_data: Optional output from analyze_smc for confluence
        """
        if not records:
            return {}

        df = pd.DataFrame(records)
        df['strike'] = df['strike'].astype(float)
        df['call_oi'] = df['call_oi'].astype(float)
        df['put_oi'] = df['put_oi'].astype(float)
        
        # 1. Calculate Basis Offset (Futures - Spot)
        snapshot_futures_price = df['underlying_price'].iloc[0] if 'underlying_price' in df.columns and pd.notnull(df['underlying_price'].iloc[0]) else None
        
        basis = 0.0
        if snapshot_futures_price and current_spot_price > 0:
            basis = float(snapshot_futures_price) - current_spot_price

        def get_zone_type(strike: float) -> str:
            if strike % 50 == 0: return "MAJOR"
            if strike % 25 == 0: return "MINOR"
            return "NORMAL"

        def map_price(strike: float) -> float:
            return float(strike) - basis

        def check_confluence(mapped_price: float) -> List[str]:
            if not smc_data: return []
            tags = []
            tolerance = 2.0 # Point-based tolerance for Gold
            
            # OB Confluence
            for ob in smc_data.get('order_blocks', []):
                if ob.get('bottom', 0) - tolerance <= mapped_price <= ob.get('top', 0) + tolerance:
                    tags.append(f"OB_{ob['type'].upper()}")
            
            # FVG Confluence
            for fvg in smc_data.get('fvgs', []):
                if fvg.get('bottom', 0) - tolerance <= mapped_price <= fvg.get('top', 0) + tolerance:
                    tags.append(f"FVG_{fvg['type'].upper()}")
            
            # Fib Confluence
            fibs = smc_data.get('auto_fibs', {})
            for level, price in fibs.items():
                if abs(price - mapped_price) <= tolerance:
                    tags.append(f"FIB_{level}")
            
            return list(set(tags))

        # 2. Identify Gamma Walls (Strikes with Max OI)
        max_call_oi = df.loc[df['call_oi'].idxmax()]
        max_put_oi = df.loc[df['put_oi'].idxmax()]
        
        levels = []
        
        # Major Call Wall (Resistance)
        mapped_call = map_price(max_call_oi['strike'])
        levels.append(GammaLevel(
            price=mapped_call,
            strike=max_call_oi['strike'],
            type='CALL_WALL',
            zone_type=get_zone_type(max_call_oi['strike']),
            strength=max_call_oi['call_oi'],
            description=f"Major Resistance (Call Wall) at {max_call_oi['strike']}",
            dte=int(max_call_oi['dte']) if 'dte' in max_call_oi else None,
            confluence=check_confluence(mapped_call)
        ))

        # Major Put Wall (Support)
        mapped_put = map_price(max_put_oi['strike'])
        levels.append(GammaLevel(
            price=mapped_put,
            strike=max_put_oi['strike'],
            type='PUT_WALL',
            zone_type=get_zone_type(max_put_oi['strike']),
            strength=max_put_oi['put_oi'],
            description=f"Major Support (Put Wall) at {max_put_oi['strike']}",
            dte=int(max_put_oi['dte']) if 'dte' in max_put_oi else None,
            confluence=check_confluence(mapped_put)
        ))

        # 3. Calculate Gamma Exposure (GEX) Profile
        # simplified Net OI (Call - Put) as proxy
        total_call_oi = df['call_oi'].sum()
        total_put_oi = df['put_oi'].sum()
        
        df_sorted = df.sort_values('strike')
        gamma_flip_row = df_sorted.iloc[(df_sorted['call_oi'] - df_sorted['put_oi']).abs().argsort()[:1]]
        gamma_flip_level = gamma_flip_row['strike'].values[0] if not gamma_flip_row.empty else None

        if gamma_flip_level:
            mapped_flip = map_price(gamma_flip_level)
            levels.append(GammaLevel(
                price=mapped_flip,
                strike=gamma_flip_level,
                type='GAMMA_FLIP',
                zone_type=get_zone_type(gamma_flip_level),
                strength=0,
                description=f"Estimated Gamma Flip at {gamma_flip_level}",
                confluence=check_confluence(mapped_flip)
            ))

        regime_type = 'POSITIVE_GAMMA' if current_spot_price > (gamma_flip_level or 0) else 'NEGATIVE_GAMMA'
        
        regime = MarketRegime(
            net_gex=total_call_oi - total_put_oi, # Raw Net OI as proxy
            regime=regime_type,
            gamma_flip_level=gamma_flip_level,
            summary=f"Market is in {regime_type} regime. Net OI Delta: {total_call_oi - total_put_oi:,.0f}"
        )

        return {
            "levels": levels,
            "regime": regime,
            "raw_data": df.to_dict(orient='records')
        }
