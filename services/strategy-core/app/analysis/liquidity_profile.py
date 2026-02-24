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
        df['strike'] = df['strike'].astype('float32')
        df['call_oi'] = df['call_oi'].astype('float32')
        df['put_oi'] = df['put_oi'].astype('float32')
        
        # 1. First, identify global Call/Put walls BEFORE filtering
        # This ensures we don't lose major levels that are far from the spot
        max_call_row = df.loc[df['call_oi'].idxmax()]
        max_put_row = df.loc[df['put_oi'].idxmax()]
        max_oi_overall = max(df['call_oi'].max(), df['put_oi'].max()) or 1.0

        # 2. Filter strikes near current_spot_price to optimize Max Pain and Heatmap
        # Range: +/- $300 (Standard for Gold)
        filter_range = 300.0
        df_filtered = df[
            (df['strike'] >= current_spot_price - filter_range) & 
            (df['strike'] <= current_spot_price + filter_range)
        ]

        # If filtering is too aggressive, fallback to a wider range or full data
        if len(df_filtered) < 10:
             df_filtered = df

        # 3. Calculate Basis Offset (Futures - Spot)
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

        # 4. Construct Gamma Levels
        levels = []
        
        # Major Call Wall (Resistance)
        mapped_call = map_price(max_call_row['strike'])
        call_conf = check_confluence(mapped_call)
        dte_val = int(max_call_row['dte']) if 'dte' in max_call_row and pd.notnull(max_call_row['dte']) else None
        levels.append(GammaLevel(
            price=mapped_call,
            strike=max_call_row['strike'],
            type='CALL_WALL',
            zone_type=get_zone_type(max_call_row['strike']),
            strength=float(max_call_row['call_oi']),
            description=f"Major Resistance (Call Wall) at {max_call_row['strike']}",
            dte=dte_val,
            term=self.categorize_dte(dte_val),
            market_action="RESISTANCE",
            zone_type_v2="SUPPLY_ZONE" if max_call_row['call_oi'] > max_call_row['put_oi'] * 1.5 else "NEUTRAL",
            significance_score=self.calculate_significance('CALL_WALL', get_zone_type(max_call_row['strike']), call_conf, max_call_row['call_oi']/max_oi_overall),
            confluence=call_conf
        ))

        # Major Put Wall (Support)
        mapped_put = map_price(max_put_row['strike'])
        put_conf = check_confluence(mapped_put)
        dte_val = int(max_put_row['dte']) if 'dte' in max_put_row and pd.notnull(max_put_row['dte']) else None
        levels.append(GammaLevel(
            price=mapped_put,
            strike=max_put_row['strike'],
            type='PUT_WALL',
            zone_type=get_zone_type(max_put_row['strike']),
            strength=float(max_put_row['put_oi']),
            description=f"Major Support (Put Wall) at {max_put_row['strike']}",
            dte=dte_val,
            term=self.categorize_dte(dte_val),
            market_action="SUPPORT",
            zone_type_v2="DEMAND_ZONE" if max_put_row['put_oi'] > max_put_row['call_oi'] * 1.5 else "NEUTRAL",
            significance_score=self.calculate_significance('PUT_WALL', get_zone_type(max_put_row['strike']), put_conf, max_put_row['put_oi']/max_oi_overall),
            confluence=put_conf
        ))

        # 5. GEX Regime
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
            net_gex=total_call_oi - total_put_oi,
            regime=regime_type,
            gamma_flip_level=gamma_flip_level,
            summary=f"Market is in {regime_type} regime. Net OI Delta: {total_call_oi - total_put_oi:,.0f}"
        )

        # 6. Optimized Max Pain (on filtered data)
        max_pain_strike = self.calculate_max_pain(df_filtered)
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
            "heatmap": self.calculate_oi_heatmap_data(df_filtered, basis),
            "raw_data": df_filtered.to_dict(orient='records')
        }

    def calculate_max_pain(self, df: pd.DataFrame) -> float:
        """
        Calculates the Max Pain strike price with O(N) complexity using cumulative sums.
        This is mathematically equivalent to the loop-based approach but far more efficient.
        """
        if df.empty: return 0.0

        # 1. Sort by strike to enable cumulative sum logic
        df_sorted = df.sort_values('strike')
        strikes = df_sorted['strike'].values
        call_oi = df_sorted['call_oi'].values
        put_oi = df_sorted['put_oi'].values

        # 2. Pre-calculate values for Calls (Loss when Price > Strike)
        # Call Loss at price S = S * sum(OI_i) - sum(K_i * OI_i) for all K_i < S
        call_oi_cumsum = np.cumsum(call_oi)
        call_ko_oi_cumsum = np.cumsum(strikes * call_oi)

        # 3. Pre-calculate values for Puts (Loss when Price < Strike)
        # Put Loss at price S = sum(K_i * OI_i) - S * sum(OI_i) for all K_i > S
        # We use reversed cumsums for Puts (summing from right to left)
        put_oi_sum = np.sum(put_oi)
        put_ko_oi_sum = np.sum(strikes * put_oi)
        
        # Cumulative sum from right to left: sum(K_i * OI_i) for all K_i >= S
        put_oi_cumsum_rev = put_oi_sum - call_oi_cumsum + call_oi # Includes current strike
        # Note: we need sum of OI for K_i > S. 
        # Actually, let's use a simpler way:
        put_oi_rev_cumsum = np.cumsum(put_oi[::-1])[::-1]
        put_ko_oi_rev_cumsum = np.cumsum((strikes * put_oi)[::-1])[::-1]

        # 4. Calculate total loss for EACH strike being the settlement price
        # For a strike S[j]:
        # Call loss = S[j] * call_oi_cumsum[j-1] - call_ko_oi_cumsum[j-1]
        # Put loss = put_ko_oi_rev_cumsum[j+1] - S[j] * put_oi_rev_cumsum[j+1]
        
        # We can vectorize this across all j
        # Shifted cumsums to handle "less than" and "greater than"
        c_oi_prev = np.concatenate([[0], call_oi_cumsum[:-1]])
        c_ko_prev = np.concatenate([[0], call_ko_oi_cumsum[:-1]])
        
        p_oi_next = np.concatenate([put_oi_rev_cumsum[1:], [0]])
        p_ko_next = np.concatenate([put_ko_oi_rev_cumsum[1:], [0]])

        call_losses = strikes * c_oi_prev - c_ko_prev
        put_losses = p_ko_next - strikes * p_oi_next
        
        total_losses = call_losses + put_losses

        # 5. Find the minimum loss
        best_index = np.argmin(total_losses)
        
        return float(strikes[best_index])

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
        
        # Convert float32 back to native float for JSON serialization
        for col in ['strike', 'mapped_price', 'call_oi', 'put_oi', 'total_oi', 'pcr', 'relative_density']:
            heatmap_df[col] = heatmap_df[col].astype(float)
            
        return heatmap_df[['strike', 'mapped_price', 'call_oi', 'put_oi', 'total_oi', 'pcr', 'relative_density']].to_dict(orient='records')

