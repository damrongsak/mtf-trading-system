import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class GammaLevel:
    price: float      # Mapped CFD/Spot Price
    strike: float     # Raw CME Strike Price
    type: str         # 'CALL_WALL' | 'PUT_WALL' | 'GAMMA_FLIP' | 'LEVEL' | 'MAX_PAIN'
    zone_type: str    # 'MAJOR' | 'MINOR' | 'NORMAL'
    strength: float   # OI or GEX value
    description: str
    dte: Optional[int] = None # Days to Expiration
    term: str = "MEDIUM_TERM" # 'SHORT_TERM' | 'MEDIUM_TERM' | 'LONG_TERM'
    market_action: str = "PIVOT" # 'SUPPORT' | 'RESISTANCE' | 'PIVOT'
    zone_type_v2: str = "NEUTRAL" # 'DEMAND_ZONE' | 'SUPPLY_ZONE' | 'NEUTRAL'
    significance_score: float = 0.5 # 0.0 to 1.0
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

    def categorize_dte(self, dte: Optional[int]) -> str:
        if dte is None: return "MEDIUM_TERM"
        if dte <= 7: return "SHORT_TERM"
        if dte <= 35: return "MEDIUM_TERM"
        return "LONG_TERM"

    def determine_market_action(self, level_type: str, dte: Optional[int]) -> str:
        if level_type == 'CALL_WALL': return "RESISTANCE"
        if level_type == 'PUT_WALL': return "SUPPORT"
        if level_type == 'MAX_PAIN': return "PIVOT"
        return "PIVOT"

    def calculate_significance(self, level_type: str, zone_type: str, confluence: List[str], relative_strength: float) -> float:
        score = 0.5
        if zone_type == "MAJOR": score += 0.2
        if confluence: score += min(0.1 * len(confluence), 0.3)
        if level_type in ['CALL_WALL', 'PUT_WALL']: score += 0.1
        return min(score, 1.0)

    def analyze_snapshot(self, records: List[Dict[str, Any]], current_spot_price: float, smc_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a list of OI records to determine levels and regime.
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
        max_oi_overall = max(df['call_oi'].max(), df['put_oi'].max()) or 1.0
        
        # Major Call Wall (Resistance)
        mapped_call = map_price(max_call_oi['strike'])
        call_conf = check_confluence(mapped_call)
        dte_val = int(max_call_oi['dte']) if 'dte' in max_call_oi and pd.notnull(max_call_oi['dte']) else None
        levels.append(GammaLevel(
            price=mapped_call,
            strike=max_call_oi['strike'],
            type='CALL_WALL',
            zone_type=get_zone_type(max_call_oi['strike']),
            strength=max_call_oi['call_oi'],
            description=f"Major Resistance (Call Wall) at {max_call_oi['strike']}",
            dte=dte_val,
            term=self.categorize_dte(dte_val),
            market_action="RESISTANCE",
            zone_type_v2="SUPPLY_ZONE" if max_call_oi['call_oi'] > max_call_oi['put_oi'] * 1.5 else "NEUTRAL",
            significance_score=self.calculate_significance('CALL_WALL', get_zone_type(max_call_oi['strike']), call_conf, max_call_oi['call_oi']/max_oi_overall),
            confluence=call_conf
        ))

        # Major Put Wall (Support)
        mapped_put = map_price(max_put_oi['strike'])
        put_conf = check_confluence(mapped_put)
        dte_val = int(max_put_oi['dte']) if 'dte' in max_put_oi and pd.notnull(max_put_oi['dte']) else None
        levels.append(GammaLevel(
            price=mapped_put,
            strike=max_put_oi['strike'],
            type='PUT_WALL',
            zone_type=get_zone_type(max_put_oi['strike']),
            strength=max_put_oi['put_oi'],
            description=f"Major Support (Put Wall) at {max_put_oi['strike']}",
            dte=dte_val,
            term=self.categorize_dte(dte_val),
            market_action="SUPPORT",
            zone_type_v2="DEMAND_ZONE" if max_put_oi['put_oi'] > max_put_oi['call_oi'] * 1.5 else "NEUTRAL",
            significance_score=self.calculate_significance('PUT_WALL', get_zone_type(max_put_oi['strike']), put_conf, max_put_oi['put_oi']/max_oi_overall),
            confluence=put_conf
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
            flip_conf = check_confluence(mapped_flip)
            levels.append(GammaLevel(
                price=mapped_flip,
                strike=gamma_flip_level,
                type='GAMMA_FLIP',
                zone_type=get_zone_type(gamma_flip_level),
                strength=0,
                description=f"Estimated Gamma Flip at {gamma_flip_level}",
                market_action="PIVOT",
                significance_score=self.calculate_significance('GAMMA_FLIP', get_zone_type(gamma_flip_level), flip_conf, 0.5),
                confluence=flip_conf
            ))

        regime_type = 'POSITIVE_GAMMA' if current_spot_price > (gamma_flip_level or 0) else 'NEGATIVE_GAMMA'
        
        regime = MarketRegime(
            net_gex=total_call_oi - total_put_oi, # Raw Net OI as proxy
            regime=regime_type,
            gamma_flip_level=gamma_flip_level,
            summary=f"Market is in {regime_type} regime. Net OI Delta: {total_call_oi - total_put_oi:,.0f}"
        )

        # 4. Calculate Max Pain
        max_pain_strike = self.calculate_max_pain(df)
        mapped_max_pain = map_price(max_pain_strike)
        pain_conf = check_confluence(mapped_max_pain)
        levels.append(GammaLevel(
            price=mapped_max_pain,
            strike=max_pain_strike,
            type='MAX_PAIN',
            zone_type=get_zone_type(max_pain_strike),
            strength=0,
            description=f"Max Pain (Options Gravity) at {max_pain_strike}",
            market_action="PIVOT",
            significance_score=self.calculate_significance('MAX_PAIN', get_zone_type(max_pain_strike), pain_conf, 0.8),
            confluence=pain_conf
        ))

        return {
            "levels": levels,
            "regime": regime,
            "max_pain": max_pain_strike,
            "mapped_max_pain": mapped_max_pain,
            "heatmap": self.calculate_oi_heatmap_data(df, basis),
            "raw_data": df.to_dict(orient='records')
        }

    def calculate_max_pain(self, df: pd.DataFrame) -> float:
        """
        Calculates the Max Pain strike price (where total loss for option buyers is minimized).
        Uses O(N) memory by iterating over potential spots.
        """
        strikes = df['strike'].unique()
        best_strike = strikes[0]
        min_loss = float('inf')

        # Vectorized calculation for each potential settlement strike
        for spot in strikes:
            # Call Loss: max(0, spot - strike) * call_oi
            call_loss = np.maximum(0, spot - df['strike']) * df['call_oi']
            # Put Loss: max(0, strike - spot) * put_oi
            put_loss = np.maximum(0, df['strike'] - spot) * df['put_oi']
            
            total_loss = float(call_loss.sum() + put_loss.sum())
            
            if total_loss < min_loss:
                min_loss = total_loss
                best_strike = spot
                
        return float(best_strike)

    def calculate_oi_heatmap_data(self, df: pd.DataFrame, basis: float = 0.0) -> List[Dict[str, Any]]:
        """
        Generates data for spatial representation of Open Interest.
        """
        heatmap_df = df.copy()
        heatmap_df['total_oi'] = heatmap_df['call_oi'] + heatmap_df['put_oi']
        heatmap_df['pcr'] = heatmap_df['put_oi'] / heatmap_df['call_oi'].replace(0, np.nan)
        heatmap_df['pcr'] = heatmap_df['pcr'].fillna(0)
        heatmap_df['mapped_price'] = heatmap_df['strike'] - basis
        
        # Calculate Relative Density (0.0 to 1.0)
        max_oi = heatmap_df['total_oi'].max()
        heatmap_df['relative_density'] = (heatmap_df['total_oi'] / max_oi) if max_oi > 0 else 0.0
        
        # Sort by strike for consistent heatmap ordering
        heatmap_df = heatmap_df.sort_values('strike')
        
        return heatmap_df[['strike', 'mapped_price', 'call_oi', 'put_oi', 'total_oi', 'pcr', 'relative_density']].to_dict(orient='records')

    def calculate_oi_heatmap_data(self, df: pd.DataFrame, basis: float = 0.0) -> List[Dict[str, Any]]:
        """
        Generates data for spatial representation of Open Interest.
        """
        heatmap_df = df.copy()
        heatmap_df['total_oi'] = heatmap_df['call_oi'] + heatmap_df['put_oi']
        heatmap_df['pcr'] = heatmap_df['put_oi'] / heatmap_df['call_oi'].replace(0, np.nan)
        heatmap_df['pcr'] = heatmap_df['pcr'].fillna(0)
        heatmap_df['mapped_price'] = heatmap_df['strike'] - basis
        
        # Calculate Relative Density (0.0 to 1.0)
        max_oi = heatmap_df['total_oi'].max()
        heatmap_df['relative_density'] = (heatmap_df['total_oi'] / max_oi) if max_oi > 0 else 0.0
        
        # Sort by strike for consistent heatmap ordering
        heatmap_df = heatmap_df.sort_values('strike')
        
        return heatmap_df[['strike', 'mapped_price', 'call_oi', 'put_oi', 'total_oi', 'pcr', 'relative_density']].to_dict(orient='records')
