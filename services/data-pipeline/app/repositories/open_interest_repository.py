from sqlalchemy.orm import Session
from sqlalchemy import func, desc, select
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from app.models.open_interest import OpenInterest
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
            func.max(OpenInterest.created_at).label('created_at')
        ).group_by(OpenInterest.snapshot_at)\
         .order_by(desc(OpenInterest.snapshot_at))\
         .limit(limit)\
         .all()

    def get_by_snapshot(self, snapshot_at: datetime, contract_symbol: Optional[str] = None, min_oi: int = 0, max_oi: Optional[int] = None, smart_filter: bool = False) -> List[OpenInterest]:
        """
        Get all Open Interest records for a specific snapshot with optional filters.
        """
        query = self.db.query(OpenInterest).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

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
        
    def get_active_strike_range(self, snapshot_at: datetime, contract_symbol: Optional[str] = None, std_dev_multiplier: float = 2.0) -> Tuple[float, float]:
        """
        Calculates the 'Active' strike range based on OI Weighted Mean and Standard Deviation.
        Returns (min_strike, max_strike).
        """
        query = select(
            OpenInterest.strike,
            (OpenInterest.call_oi + OpenInterest.put_oi).label('total_oi')
        ).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

        if contract_symbol:
            query = query.filter(OpenInterest.contract_symbol == contract_symbol)

        result = self.db.execute(query)
        rows = result.fetchall()

        if not rows:
            return (0.0, 0.0)

        # Calculate Weighted Mean
        total_oi_sum = sum(row.total_oi for row in rows if row.total_oi)
        if total_oi_sum == 0:
            return (0.0, 0.0)

        weighted_sum = sum(float(row.strike) * float(row.total_oi) for row in rows if row.total_oi)
        mean_strike = weighted_sum / float(total_oi_sum)

        # Calculate Variance / StdDev
        variance_sum = sum(float(row.total_oi) * ((float(row.strike) - mean_strike) ** 2) for row in rows if row.total_oi)
        variance = variance_sum / float(total_oi_sum)
        std_dev = variance ** 0.5

        min_strike = mean_strike - (std_dev * std_dev_multiplier)
        max_strike = mean_strike + (std_dev * std_dev_multiplier)

        return (min_strike, max_strike)

    def get_analysis_data(self, snapshot_at: datetime, contract_symbol: Optional[str] = None, min_oi: int = 0, max_oi: Optional[int] = None, smart_filter: bool = False) -> Dict[str, Any]:
        """
        Aggregates Open Interest data to calculate PCR, Max Pain, and detailed strike distribution.
        """
        # base query
        query = select(
            OpenInterest.strike,
            func.sum(OpenInterest.call_oi).label('total_call_oi'),
            func.sum(OpenInterest.put_oi).label('total_put_oi')
        ).filter(
            OpenInterest.snapshot_at == snapshot_at
        )

        if contract_symbol:
            query = query.filter(OpenInterest.contract_symbol == contract_symbol)

        # Apply Smart Strike Range Filter
        if smart_filter:
            min_k, max_k = self.get_active_strike_range(snapshot_at, contract_symbol)
            if min_k > 0:
                query = query.filter(OpenInterest.strike >= min_k, OpenInterest.strike <= max_k)

        query = query.group_by(OpenInterest.strike).order_by(OpenInterest.strike)

        # Execute
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
            
            # ... update max strikes ...
            distribution.append({
                "strike": row.strike,
                "call_oi": c_oi,
                "put_oi": p_oi,
                "total_oi": total_leg_oi,
                "net_delta": c_oi - p_oi
            })

            if c_oi > max_call_oi:
                max_call_oi = c_oi
                summary["max_call_strike"] = row.strike
            if p_oi > max_put_oi:
                max_put_oi = p_oi
                summary["max_put_strike"] = row.strike

        if summary["total_call_oi"] > 0:
            summary["pcr"] = summary["total_put_oi"] / summary["total_call_oi"]
        
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

