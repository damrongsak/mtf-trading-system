import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class GammaLevel:
    price: float
    strike: float
    type: str  # 'CALL_WALL', 'PUT_WALL', 'GAMMA_FLIP', 'major', 'minor'
    strength: float  # OI or GEX value
    description: str

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

    def analyze_snapshot(self, records: List[Dict[str, Any]], current_spot_price: float) -> Dict[str, Any]:
        """
        Analyze a list of OI records to determine levels and regime.
        
        Args:
            records: List of dicts with keys: strike, call_oi, put_oi, underlying_price (at snapshot)
            current_spot_price: Current live price of the asset (CFD/Spot)
        
        Returns:
            Dict containing 'levels' (List[GammaLevel]) and 'regime' (MarketRegime)
        """
        if not records:
            return {}

        df = pd.DataFrame(records)
        df['strike'] = df['strike'].astype(float)
        df['call_oi'] = df['call_oi'].astype(float)
        df['put_oi'] = df['put_oi'].astype(float)
        
        # 1. Calculate Offset (Futures - Spot)
        # We use the underlying_price from the snapshot time to verify the basis
        # If underlying_price is present in records (it should be equal for all records in one snapshot)
        snapshot_futures_price = df['underlying_price'].iloc[0] if 'underlying_price' in df.columns and pd.notnull(df['underlying_price'].iloc[0]) else None
        
        offset = 0.0
        if snapshot_futures_price:
            # Simple offset: Futures - Spot. 
            # NOTE: Ideally we need historical spot at snapshot time. 
            # For now, we assume the caller passes the CORRECT spot price relative to the snapshot 
            # or we calculate offset if we have the snapshot's spot price.
            # 
            # Strategy: The levels are based on FUTURES strikes. 
            # We want to map them to SPOT.
            # Spot Level = Futures Strike - (Futures Price - Spot Price)
            # THIS IS DYNAMIC. (Futures - Spot) changes constantly (Basis).
            # However, for 'Static' levels, we often pin the basis at the time of analysis or use a fixed basis.
            # Better approach: We return the LEVELS calculated from data. 
            # The STRATEGY applies the live basis correction.
            pass

        # 2. Identify Gamma Walls (Strikes with Max OI)
        max_call_oi = df.loc[df['call_oi'].idxmax()]
        max_put_oi = df.loc[df['put_oi'].idxmax()]
        
        levels = []
        
        # Major Call Wall (Resistance)
        levels.append(GammaLevel(
            price=max_call_oi['strike'], # Raw Futures Strike
            strike=max_call_oi['strike'],
            type='CALL_WALL',
            strength=max_call_oi['call_oi'],
            description=f"Major Resistance (Call Wall) at {max_call_oi['strike']}"
        ))

        # Major Put Wall (Support)
        levels.append(GammaLevel(
            price=max_put_oi['strike'], # Raw Futures Strike
            strike=max_put_oi['strike'],
            type='PUT_WALL',
            strength=max_put_oi['put_oi'],
            description=f"Major Support (Put Wall) at {max_put_oi['strike']}"
        ))

        # 3. Calculate Gamma Exposure (GEX) Profile
        # simplified GEX calculation: 
        # Call GEX = OI * Spot * 0.01 (approx gamma scalar) * C
        # Put GEX = OI * Spot * 0.01 * P
        # This is complex without Greeks.
        # Fallback: Net OI (Call - Put) as proxy for "Directional Exposure"
        
        total_call_oi = df['call_oi'].sum()
        total_put_oi = df['put_oi'].sum()
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0
        
        # Estimate Gamma Flip
        # The level where Net OI switches from Put Dominant to Call Dominant
        # We sort by strike and calculate cumulative Net OI
        df_sorted = df.sort_values('strike')
        df_sorted['net_oi'] = df_sorted['call_oi'] - df_sorted['put_oi']
        
        # Find zero crossing
        # Zero crossing in Cumulative Net OI might not be Gamma Flip. 
        # Gamma Flip is typically where Total Gamma = 0.
        # Without Greeks, a rough proxy is where Call OI ≈ Put OI (Strike with max mixed interest or where PCR flips locally).
        
        # Let's use the 'Absolute Net OI' crossover method for proxy
        # Find strike where Call OI intercepts Put OI
        gamma_flip_row = df_sorted.iloc[(df_sorted['call_oi'] - df_sorted['put_oi']).abs().argsort()[:1]]
        gamma_flip_level = gamma_flip_row['strike'].values[0] if not gamma_flip_row.empty else None

        if gamma_flip_level:
            levels.append(GammaLevel(
                price=gamma_flip_level,
                strike=gamma_flip_level,
                type='GAMMA_FLIP',
                strength=0,
                description=f"Estimated Gamma Flip at {gamma_flip_level}"
            ))

        # Regime
        # If Price > Flip -> Positive Gamma (Calls dominate) -> Mean Reversion
        # If Price < Flip -> Negative Gamma (Puts dominate) -> Volatility
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
