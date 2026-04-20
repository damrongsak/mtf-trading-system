import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
from app.utils.options_math import black_scholes_greeks
from app.utils.vol_surface import get_gvz_index, get_synthetic_iv, get_vanna_charm_sensitivity


logger = logging.getLogger(__name__)

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
    # V3.0 Greeks
    iv: Optional[float] = None
    vanna: Optional[float] = None
    charm: Optional[float] = None
    fragility_score: float = 0.0


@dataclass
class MarketRegime:
    net_gex: float
    regime: str  # 'POSITIVE_GAMMA' (Mean Reversion) or 'NEGATIVE_GAMMA' (Volatile/Trend)
    gamma_flip_level: Optional[float]
    summary: str
    is_valid: bool = True
    integrity_alerts: List[str] = field(default_factory=list)
    # V3.0 Metrics
    fragility_index: float = 0.0 # 0-100 LFI
    fragility_alert: str = "STABLE"
    total_vanna_exposure: float = 0.0
    total_charm_decay: float = 0.0


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

    def analyze_snapshot(
        self, 
        records: List[Dict[str, Any]], 
        current_spot_price: float, 
        smc_data: Optional[Dict[str, Any]] = None,
        target_contract: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze OI records to determine levels and regime using vectorized operations.
        
        Args:
            target_contract: If provided, only analyzes this specific contract (e.g. 'OGM6').
                             If None, it analyzes the 'Active' contract (highest OI).
        """
        if not records:
            return {}

        df = pd.DataFrame(records)
        df['strike'] = df['strike'].astype('float64')
        df['call_oi'] = df['call_oi'].astype('float64')
        df['put_oi'] = df['put_oi'].astype('float64')
        df['total_oi'] = df['call_oi'] + df['put_oi']
        
        # 1. Identify Target Contract Group
        if not target_contract:
            # Group by contract_symbol and find one with highest total OI
            target_contract = df.groupby('contract_symbol')['total_oi'].sum().idxmax()
        
        df_target = df[df['contract_symbol'] == target_contract].copy()
        
        if df_target.empty:
            logger.warning(f"No records found for target contract: {target_contract}")
            return {}

        # 2. Vectorized Basis Calculation (Futures - Spot)
        # Using explicit mapping from the records
        underlying_prices = df_target['underlying_price'].dropna()
        if not underlying_prices.empty:
            snapshot_futures_price = float(underlying_prices.iloc[0])
            basis = snapshot_futures_price - current_spot_price
        else:
            basis = 0.0
            
        df_target['mapped_price'] = df_target['strike'] - basis
        
        # 3. GEX & Greeks (V3.0 Institutional Standard)
        # Distance-Weighted GEX Proxy
        pct_distance = np.abs(df_target['strike'] - current_spot_price) / current_spot_price * 100.0
        # Weight exponentially favors At-The-Money (ATM) strikes
        weights = 1.0 / (1.0 + pct_distance ** 2)
        weighted_net = (df_target['call_oi'] - df_target['put_oi']) * weights
        net_gex = float(weighted_net.sum())
        total_gex = float(np.abs(weighted_net).sum())
        
        # Synthetic IV & Greeks
        atm_iv = get_gvz_index()
        df_target['iv'] = get_synthetic_iv(current_spot_price, df_target['mapped_price'], atm_iv)
        
        # Calculate Greeks for each strike
        greeks_list = []
        for _, row in df_target.iterrows():
            option_type = 'CALL' if row['call_oi'] >= row['put_oi'] else 'PUT'
            # T (Years to Expiry) - Approx from DTE
            t_years = max(row['dte'], 1) / 365.25
            gref = black_scholes_greeks(
                S=current_spot_price,
                K=row['mapped_price'], 
                T=t_years,
                r=0.045, # Global Risk-Free Proxy
                sigma=row['iv'],
                option_type=option_type
            )
            greeks_list.append(gref)
        
        greeks_df = pd.DataFrame(greeks_list)
        df_target = pd.concat([df_target.reset_index(drop=True), greeks_df.reset_index(drop=True)], axis=1)
        
        # Calculate Total Exposures
        # Vanna Exposure = Sum(Vanna * OI)
        df_target['vanna_exposure'] = df_target['vanna'] * df_target['total_oi']
        df_target['charm_decay'] = df_target['charm'] * df_target['total_oi']
        
        total_vanna = float(df_target['vanna_exposure'].sum())
        total_charm = float(df_target['charm_decay'].sum())
        
        # Calculate Liquidity Fragility Index (LFI)
        # Higher absolute Vanna/Charm relative to GEX implies fragile walls
        lfi = 0.0
        if total_gex > 0:
            # Normalize sensitivities to GEX magnitude
            v_sens = abs(total_vanna) / (total_gex * 0.1)
            c_sens = abs(total_charm) / (total_gex * 0.01)
            lfi = min((v_sens + c_sens) * 50, 100.0)


        # 4. Identify Walls (Local vs Global)
        # Global Walls (Absolute maximums)
        max_call_row = df_target.loc[df_target['call_oi'].idxmax()]
        max_put_row = df_target.loc[df_target['put_oi'].idxmax()]
        max_oi_overall = df_target['total_oi'].max() or 1.0

        # Primary Walls (Nearest to Spot - +/- 10% range)
        local_range = current_spot_price * 0.10
        df_local = df_target[
            (df_target['mapped_price'] >= current_spot_price - local_range) & 
            (df_target['mapped_price'] <= current_spot_price + local_range)
        ]
        
        if not df_local.empty:
            primary_call_row = df_local.loc[df_local['call_oi'].idxmax()]
            primary_put_row = df_local.loc[df_local['put_oi'].idxmax()]
        else:
            primary_call_row = max_call_row
            primary_put_row = max_put_row

        # 5. Filter relevant strikes for Max Pain / Heatmap (+/- 15% standard)
        price_range_pain = current_spot_price * 0.15
        df_filtered = df_target[
            (df_target['mapped_price'] >= current_spot_price - price_range_pain) & 
            (df_target['mapped_price'] <= current_spot_price + price_range_pain)
        ]
        
        if len(df_filtered) < 5:
            df_filtered = df_target

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
        # 6. Construct Gamma Levels
        levels = []
        
        def check_confluence_vec(mapped_prices: np.ndarray) -> List[List[str]]:
            if not smc_data: return [[] for _ in range(len(mapped_prices))]
            results = []
            tolerance = 2.0
            obs = smc_data.get('order_blocks', [])
            fvgs = smc_data.get('fvgs', [])
            fibs = smc_data.get('auto_fibs', {})
            
            for p in mapped_prices:
                tags = []
                for ob in obs:
                    if ob['bottom'] - tolerance <= p <= ob['top'] + tolerance:
                        tags.append(f"OB_{ob['type'].upper()}")
                for fvg in fvgs:
                    if fvg['bottom'] - tolerance <= p <= fvg['top'] + tolerance:
                        tags.append(f"FVG_{fvg['type'].upper()}")
                for level, price in fibs.items():
                    if abs(float(price) - p) <= tolerance:
                        tags.append(f"FIB_{level}")
                results.append(list(set(tags)))
            return results

        # Primary Resistance (Local Call Wall)
        p_call_conf = check_confluence_vec(np.array([primary_call_row['mapped_price']]))[0]
        dte_val = int(primary_call_row['dte']) if pd.notnull(primary_call_row['dte']) else None
        levels.append(GammaLevel(
            price=float(primary_call_row['mapped_price']),
            strike=float(primary_call_row['strike']),
            type='CALL_WALL',
            zone_type=get_zone_type(primary_call_row['strike']),
            strength=float(primary_call_row['call_oi']),
            description=f"Primary Resistance (Local Call Wall) at {primary_call_row['strike']}",
            dte=dte_val,
            term=self.categorize_dte(dte_val),
            market_action="RESISTANCE",
            zone_type_v2="SUPPLY_ZONE",
            significance_score=self.calculate_significance('CALL_WALL', get_zone_type(primary_call_row['strike']), p_call_conf, primary_call_row['call_oi']/max_oi_overall),
            confluence=p_call_conf,
            iv=float(primary_call_row['iv']),
            vanna=float(primary_call_row['vanna']),
            charm=float(primary_call_row['charm'])
        ))


        # Major Resistance (Absolute Call Wall)
        if primary_call_row['strike'] != max_call_row['strike']:
            m_call_conf = check_confluence_vec(np.array([max_call_row['mapped_price']]))[0]
            levels.append(GammaLevel(
                price=float(max_call_row['mapped_price']),
                strike=float(max_call_row['strike']),
                type='CALL_WALL',
                zone_type="MAJOR",
                strength=float(max_call_row['call_oi']),
                description=f"Major Institutional Resistance at {max_call_row['strike']}",
                market_action="RESISTANCE",
                zone_type_v2="SUPPLY_ZONE",
                significance_score=0.9,
                confluence=m_call_conf
            ))

        # Primary Support (Local Put Wall)
        p_put_conf = check_confluence_vec(np.array([primary_put_row['mapped_price']]))[0]
        dte_val = int(primary_put_row['dte']) if pd.notnull(primary_put_row['dte']) else None
        levels.append(GammaLevel(
            price=float(primary_put_row['mapped_price']),
            strike=float(primary_put_row['strike']),
            type='PUT_WALL',
            zone_type=get_zone_type(primary_put_row['strike']),
            strength=float(primary_put_row['put_oi']),
            description=f"Primary Support (Local Put Wall) at {primary_put_row['strike']}",
            dte=dte_val,
            term=self.categorize_dte(dte_val),
            market_action="SUPPORT",
            zone_type_v2="DEMAND_ZONE",
            significance_score=self.calculate_significance('PUT_WALL', get_zone_type(primary_put_row['strike']), p_put_conf, primary_put_row['put_oi']/max_oi_overall),
            confluence=p_put_conf
        ))

        # Absolute Floor (Global Put Wall)
        if primary_put_row['strike'] != max_put_row['strike']:
            m_put_conf = check_confluence_vec(np.array([max_put_row['mapped_price']]))[0]
            levels.append(GammaLevel(
                price=float(max_put_row['mapped_price']),
                strike=float(max_put_row['strike']),
                type='PUT_WALL',
                zone_type="MAJOR",
                strength=float(max_put_row['put_oi']),
                description=f"Absolute Institutional Floor at {max_put_row['strike']}",
                market_action="SUPPORT",
                zone_type_v2="DEMAND_ZONE",
                significance_score=0.9,
                confluence=m_put_conf
            ))

        # 6. Sentiment Context
        total_call_oi = df_target['call_oi'].sum()
        total_put_oi = df_target['put_oi'].sum()
        
        # 4. Calculate Gamma Flip (OIWAP Method for Stability - V2.5 Standard)
        # Filter for active strikes to avoid picking strikes with zero OI
        df_sorted = df_target.sort_values('strike')
        df_active = df_sorted[df_sorted['total_oi'] > 0].copy()
        
        gamma_flip_level = current_spot_price # Default
        integrity_alerts = []
        
        if not df_active.empty:
            # OIWAP: OI-Weighted Average Price
            # This provides a more robust 'center of gravity' for dealer hedging
            total_oi_weighted_sum = (df_active['strike'] * df_active['total_oi']).sum()
            total_active_oi = df_active['total_oi'].sum()
            
            if total_active_oi > 0:
                gamma_flip_level = float(total_oi_weighted_sum / total_active_oi)
        
        # 5. Reality-Anchoring & Regime Validation (V2.5 Standard)
        is_valid = True
        
        # Check 1: Reality Anchoring (Stale Price Protection)
        if current_spot_price > 0 and snapshot_futures_price > 0:
            divergence = abs(current_spot_price - snapshot_futures_price) / current_spot_price
            if divergence > 0.20:
                is_valid = False
                integrity_alerts.append("STALE_OR_SCALE_DIVERGENCE")
        
        # Check 2: Low Liquidity Floor
        if total_gex < 1.0: # Arbitrary noise floor for institutional relevance
            is_valid = False
            integrity_alerts.append("LOW_LIQUIDITY_NOISE_FLOOR")
            
        # Check 3: Mathematical Impossibility
        if gamma_flip_level > 0 and current_spot_price > 0:
            flip_dist = abs(gamma_flip_level - current_spot_price) / current_spot_price
            if flip_dist > 0.25: # Flip point should be within reasonable proximity
                is_valid = False
                integrity_alerts.append("IMPOSSIBLE_FLIP_PROXIMITY")

        # 6. Final Outputs
        regime_type = 'POSITIVE_GAMMA' if net_gex > 0 else 'NEGATIVE_GAMMA'
        
        # Add Gamma Flip to Levels (V2.5 Mapping)
        if gamma_flip_level:
            mapped_flip = gamma_flip_level - basis
            flip_conf = check_confluence_vec(np.array([mapped_flip]))[0]
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

        regime_summary = f"Market is in {regime_type} regime for {target_contract}. Net Distance-Weighted GEX: {net_gex:,.0f} (Raw Call: {total_call_oi:,.0f}, Raw Put: {total_put_oi:,.0f})"
        if not is_valid:
            regime_summary = f"⚠️ DATA_INTEGRITY_ALERT ({', '.join(integrity_alerts)}): " + regime_summary

        regime = MarketRegime(
            net_gex=net_gex,
            regime=regime_type,
            gamma_flip_level=gamma_flip_level,
            summary=regime_summary,
            is_valid=is_valid,
            integrity_alerts=integrity_alerts,
            fragility_index=lfi,
            fragility_alert=get_vanna_charm_sensitivity(lfi),
            total_vanna_exposure=total_vanna,
            total_charm_decay=total_charm
        )


        # 7. Optimized Max Pain (on filtered data)
        max_pain_strike = self.calculate_max_pain(df_filtered)
        mapped_max_pain = max_pain_strike - basis
        pain_conf = check_confluence_vec(np.array([mapped_max_pain]))[0]
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
            "target_contract": target_contract,
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

