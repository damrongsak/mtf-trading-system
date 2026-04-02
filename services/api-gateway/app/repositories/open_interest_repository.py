from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc, select
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from app.models.open_interest import OpenInterest
from app.utils.quant import calculate_black_scholes_gamma
import logging

logger = logging.getLogger(__name__)

class OpenInterestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_snapshots(self, limit: int = 20):
        """
        Get list of available Open Interest snapshots.
        """
        return self.db.query(
            OpenInterest.snapshot_at,
            func.count(OpenInterest.id).label('count'),
            func.max(OpenInterest.created_at).label('created_at'),
            func.max(OpenInterest.underlying_price).label('underlying_price')
        ).group_by(OpenInterest.snapshot_at)\
         .order_by(desc(OpenInterest.snapshot_at))\
         .limit(limit)\
         .all()

    def get_by_snapshot(self, snapshot_at: datetime, contract_symbol: Optional[str] = None, min_oi: int = 0, max_oi: Optional[int] = None, smart_filter: bool = False, min_dte: Optional[int] = None, max_dte: Optional[int] = None) -> List[OpenInterest]:
        """
        Get all Open Interest records for a specific snapshot with optional filters.
        """
        query = self.db.query(OpenInterest).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

        if min_dte:
            query = query.filter(OpenInterest.dte >= min_dte)
        if max_dte:
            query = query.filter(OpenInterest.dte <= max_dte)

        if contract_symbol:
            query = query.filter(OpenInterest.contract_symbol == contract_symbol)

        # Apply Total OI Filter (Call + Put)
        if min_oi > 0:
            query = query.filter((OpenInterest.call_oi + OpenInterest.put_oi) >= min_oi)
        
        if max_oi is not None:
            query = query.filter((OpenInterest.call_oi + OpenInterest.put_oi) <= max_oi)

        if smart_filter:
            min_k, max_k = self.get_active_strike_range(snapshot_at, contract_symbol)
            if min_k > 0:
                query = query.filter(OpenInterest.strike >= min_k, OpenInterest.strike <= max_k)

        return query.order_by(OpenInterest.strike).all()
        
    def get_active_strike_range(self, snapshot_at: datetime, contract_symbol: Optional[str] = None, std_dev_multiplier: float = 2.0, min_dte: Optional[int] = None, max_dte: Optional[int] = None) -> Tuple[float, float]:
        """
        Calculates the 'Active' strike range based on OI Weighted Mean and Standard Deviation.
        """
        total_oi_expr = func.coalesce(OpenInterest.call_oi, 0) + func.coalesce(OpenInterest.put_oi, 0)
        
        query = select(
            func.sum(total_oi_expr).label('sum_oi'),
            func.sum(OpenInterest.strike * total_oi_expr).label('sum_w_x'),
            func.sum(OpenInterest.strike * OpenInterest.strike * total_oi_expr).label('sum_w_x2')
        ).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

        if min_dte:
            query = query.filter(OpenInterest.dte >= min_dte)
        if max_dte:
            query = query.filter(OpenInterest.dte <= max_dte)

        if contract_symbol:
            query = query.filter(OpenInterest.contract_symbol == contract_symbol)

        res = self.db.execute(query).fetchone()
        if not res or not res.sum_oi or float(res.sum_oi) == 0:
            return (0.0, 0.0)

        sum_oi = float(res.sum_oi)
        mean_strike = float(res.sum_w_x) / sum_oi
        mean_sq_strike = float(res.sum_w_x2) / sum_oi

        variance = mean_sq_strike - (mean_strike ** 2)
        std_dev = variance ** 0.5 if variance > 0 else 0

        min_strike = mean_strike - (std_dev * std_dev_multiplier)
        max_strike = mean_strike + (std_dev * std_dev_multiplier)

        return (min_strike, max_strike)

    def get_analysis_data(self, snapshot_at: datetime, contract_symbol: Optional[str] = None, min_oi: int = 0, max_oi: Optional[int] = None, smart_filter: bool = False, min_dte: Optional[int] = None, max_dte: Optional[int] = None) -> Dict[str, Any]:
        """
        Aggregates Open Interest data to calculate PCR, Max Pain, and detailed strike distribution.
        """
        query = select(
            OpenInterest.strike,
            func.sum(OpenInterest.call_oi).label('total_call_oi'),
            func.sum(OpenInterest.put_oi).label('total_put_oi')
        ).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

        if min_dte:
            query = query.filter(OpenInterest.dte >= min_dte)
        if max_dte:
            query = query.filter(OpenInterest.dte <= max_dte)

        if contract_symbol:
            query = query.filter(OpenInterest.contract_symbol == contract_symbol)

        if smart_filter:
            min_k, max_k = self.get_active_strike_range(snapshot_at, contract_symbol)
            if min_k > 0:
                query = query.filter(OpenInterest.strike >= min_k, OpenInterest.strike <= max_k)

        query = query.group_by(OpenInterest.strike).order_by(OpenInterest.strike)

        result = self.db.execute(query)
        rows = result.fetchall()

        distribution = []
        summary = {
            "total_call_oi": 0,
            "total_put_oi": 0,
            "pcr": 0.0,
            "max_call_strike": 0,
            "max_put_strike": 0
        }

        max_call_oi = 0
        max_put_oi = 0

        # OIWAP Accumulators
        sum_weighted_strike = 0.0
        sum_total_oi = 0.0

        for row in rows:
            c_oi = float(row.total_call_oi or 0)
            p_oi = float(row.total_put_oi or 0)
            total_leg_oi = c_oi + p_oi

            # Apply OI filters (Post-Aggregation or Pre? Pre is better but grouped sum is hard to filter pre without subquery)
            # Doing post-filter here for simplicity with aggregated sums
            if total_leg_oi < min_oi:
                continue
            if max_oi is not None and total_leg_oi > max_oi:
                continue

            summary["total_call_oi"] += c_oi
            summary["total_put_oi"] += p_oi
            
            # Accumulate for OIWAP
            sum_weighted_strike += (float(row.strike) * total_leg_oi)
            sum_total_oi += total_leg_oi
            
            distribution.append({
                "strike": row.strike,
                "call_oi": c_oi,
                "put_oi": p_oi,
                "total_oi": total_leg_oi,
                "net_delta": c_oi - p_oi
            })

            if c_oi > max_call_oi:
                max_call_oi = c_oi
                summary["max_call_strike"] = float(row.strike)
            if p_oi > max_put_oi:
                max_put_oi = p_oi
                summary["max_put_strike"] = float(row.strike)

        if summary["total_call_oi"] > 0:
            summary["pcr"] = summary["total_put_oi"] / summary["total_call_oi"]
        
        # Calculate OIWAP
        summary["oiwap"] = sum_weighted_strike / sum_total_oi if sum_total_oi > 0 else 0.0
        
        return {
            "summary": summary,
            "distribution": distribution
        }

    def get_available_contracts(self, snapshot_at: datetime) -> List[str]:
        """
        Get list of distinct contract symbols (expiries) for a snapshot.
        """
        results = self.db.query(OpenInterest.contract_symbol)\
            .filter(OpenInterest.snapshot_at == snapshot_at)\
            .distinct()\
            .order_by(OpenInterest.contract_symbol)\
            .all()
        return [r[0] for r in results]

    def get_drift_analysis(self, latest_snapshot: datetime, prev_snapshot: datetime, contract_symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates drift metrics between two OI snapshots.
        """
        latest = self.get_analysis_data(latest_snapshot, contract_symbol=contract_symbol)
        prev = self.get_analysis_data(prev_snapshot, contract_symbol=contract_symbol)

        lat_sum = latest.get("summary", {})
        pre_sum = prev.get("summary", {})

        # Sentiment Drift
        pcr_drift = lat_sum.get("pcr", 1.0) - pre_sum.get("pcr", 1.0)
        
        lat_net = lat_sum.get("total_call_oi", 0) - lat_sum.get("total_put_oi", 0)
        pre_net = pre_sum.get("total_call_oi", 0) - pre_sum.get("total_put_oi", 0)
        net_drift = lat_net - pre_net

        # Wall Migration
        cw_shift = lat_sum.get("max_call_strike", 0.0) - pre_sum.get("max_call_strike", 0.0)
        pw_shift = lat_sum.get("max_put_strike", 0.0) - pre_sum.get("max_put_strike", 0.0)
        
        # OIWAP Migration
        oiwap_shift = lat_sum.get("oiwap", 0.0) - pre_sum.get("oiwap", 0.0)

        return {
            "pcr_drift": round(pcr_drift, 4),
            "net_oi_drift": net_drift,
            "call_wall_shift": cw_shift,
            "put_wall_shift": pw_shift,
            "oiwap_shift": round(oiwap_shift, 2),
            "sentiment": "Bullish Shift" if net_drift > 0 else "Bearish Shift",
            "latest_summary": lat_sum,
            "prev_summary": pre_sum
        }

    def get_gex_analysis_data(
        self, 
        snapshot_at: datetime, 
        contract_symbol: Optional[str] = None, 
        sigma: float = 0.16, 
        r: float = 0.05, 
        min_dte: Optional[int] = None, 
        max_dte: Optional[int] = None,
        spot_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculates GEX Surface and Gamma Flip Point for a snapshot.
        """
        # --- Initialization (Safety against UnboundLocalError) ---
        total_gex_val = 0.0
        flip_point = 0.0
        gex_dist = []
        nearest_dte = 0.0
        spot = spot_price or 0.0
        regime = "NEUTRAL"
        
        # 1. Resolve target contracts and DTE range
        # If a range is provided, we NEVER pin to a single contract unless explicitly requested.
        targeting_range = (min_dte is not None or max_dte is not None)
        
        if not contract_symbol and not targeting_range:
            # AUTO-RESOLVER: Default to the highest OI contract ONLY if no DTE range is specified.
            oi_rank = (
                select(OpenInterest.contract_symbol, func.min(OpenInterest.dte).label('dte'))
                .filter(OpenInterest.snapshot_at == snapshot_at)
                .group_by(OpenInterest.contract_symbol)
                # We often want the front month first if no range is given
                .order_by(asc('dte'))
            )
            top_contract = self.db.execute(oi_rank).fetchone()
            if top_contract:
                contract_symbol = top_contract[0]
                logger.info(f"GEX: Auto-resolver selected nearest front-month: {contract_symbol}")
        
        # Build DTE discovery query
        dte_query = select(OpenInterest.dte).filter(OpenInterest.snapshot_at == snapshot_at)
        if contract_symbol:
            dte_query = dte_query.filter(OpenInterest.contract_symbol == contract_symbol)
        if min_dte is not None:
            dte_query = dte_query.filter(OpenInterest.dte >= min_dte)
        if max_dte is not None:
            dte_query = dte_query.filter(OpenInterest.dte <= max_dte)
        
        available_dtes = [float(x[0]) for x in self.db.execute(dte_query.distinct()).fetchall()]
        if not available_dtes:
            logger.warning(f"GEX: No data found for snapshot {snapshot_at} with filters symbol={contract_symbol}, dte_range={min_dte}-{max_dte}")
            return {
                "snapshot_at": snapshot_at,
                "spot_price": spot or 0.0,
                "total_gex": 0.0, 
                "gamma_flip": 0.0, 
                "distribution": [],
                "nearest_dte": 0.0,
                "max_dte": 0.0,
                "regime": "NEUTRAL"
            }
            
        nearest_dte = min(available_dtes)
        
        # 2. Main Query Construction
        query = select(
            OpenInterest.strike,
            OpenInterest.dte,
            func.sum(OpenInterest.call_oi).label('call_oi'),
            func.sum(OpenInterest.put_oi).label('put_oi'),
            func.avg(OpenInterest.underlying_price).label('underlying_price')
        ).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

        if contract_symbol:
            query = query.filter(OpenInterest.contract_symbol == contract_symbol)
        
        if min_dte is not None:
            query = query.filter(OpenInterest.dte >= min_dte)
        if max_dte is not None:
            query = query.filter(OpenInterest.dte <= max_dte)
        elif not targeting_range and not contract_symbol:
            # Global fallback: Default to Quarterly (90 days)
            query = query.filter(OpenInterest.dte <= 90)

        query = query.group_by(OpenInterest.strike, OpenInterest.dte).order_by(OpenInterest.strike)
        
        rows = self.db.execute(query).fetchall()
        if not rows:
            return {
                "snapshot_at": snapshot_at,
                "spot_price": spot_price or 0.0,
                "total_gex": 0.0, 
                "gamma_flip": 0.0, 
                "distribution": [],
                "nearest_dte": nearest_dte,
                "max_dte": 90 if max_dte is None else max_dte,
                "regime": "NEUTRAL"
            }

        # 3. Spot Price Selection
        # If spot still 0, calculate from average underlying
        if spot <= 0:
            spot = sum(float(r.underlying_price or 0) for r in rows) / len(rows)
        
        # 4. GEX Calculation & Strike Windowing
        gex_dist = []
        total_gex_val = 0.0
        
        # INSTITUTIONAL FILTER: Group by strike and calculate total net OI to identify significance
        total_net_oi = sum(float(r.call_oi or 0) + float(r.put_oi or 0) for r in rows)
        significance_threshold = total_net_oi * 0.01  # 1% Significance Threshold
        
        for row in rows:
            strike = float(row.strike)
            
            # STRIKE WINDOWING: Ignore strikes more than 20% away from spot (Standard Institutional Window)
            # This prevents stale deep ITM/OTM strikes (like $550 for a $4700 spot) from creating artifacts
            if abs(strike - spot) / spot > 0.20:
                continue
                
            c_oi = float(row.call_oi or 0)
            p_oi = float(row.put_oi or 0)
            
            # SIGNIFICANCE FILTER: Ignore strikes with less than 1% of total surface OI
            if (c_oi + p_oi) < significance_threshold:
                continue
                
            dte = int(row.dte)
            T = dte / 365.25 # Years
            
            # Handle T=0 for expiration day
            if T <= 0: T = 0.00001
            
            gamma = calculate_black_scholes_gamma(spot, strike, T, r, sigma)
            
            # GEX = OI * Gamma * 100 * Spot
            call_gex = c_oi * gamma * 100 * spot
            put_gex = p_oi * gamma * 100 * spot * -1
            strike_gex = call_gex + put_gex
            
            total_gex_val += strike_gex
            
            gex_dist.append({
                "strike": strike,
                "dte": dte,
                "call_gex": call_gex,
                "put_gex": put_gex,
                "net_gex": strike_gex
            })

        # B. Find Zero Crossing (Gamma Flip)
        # Only look for flip if we have at least 2 strikes (for interpolation)
        if len(gex_dist) >= 2:
            # Sort by strike for linear search
            gex_dist = sorted(gex_dist, key=lambda x: x["strike"])
            
            for i in range(len(gex_dist) - 1):
                g1 = gex_dist[i]["net_gex"]
                g2 = gex_dist[i+1]["net_gex"]
                k1 = gex_dist[i]["strike"]
                k2 = gex_dist[i+1]["strike"]
                
                if (g1 < 0 and g2 > 0) or (g1 > 0 and g2 < 0):
                    # Linear interpolation for zero crossing
                    # Safety check for division by zero
                    if abs(g2 - g1) > 1e-9:
                        flip_point = k1 - g1 * (k2 - k1) / (g2 - g1)
                        break

        # C. Sentiment/Regime
        regime = "LONG_GAMMA" if total_gex_val > 0 else "SHORT_GAMMA"
        if abs(total_gex_val) < 1e-6: regime = "NEUTRAL"

        return {
            "snapshot_at": snapshot_at,
            "spot_price": spot,
            "total_gex": total_gex_val,
            "gamma_flip": flip_point,
            "regime": regime,
            "distribution": gex_dist,
            "nearest_dte": nearest_dte,
            "max_dte": max_dte if max_dte is not None else (90 if min_dte is None else 999)
        }
