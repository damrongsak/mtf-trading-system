from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import logging
from app.schemas import GapDiscoveryResponse, GapInfo
from app.models.market import MarketSymbol

logger = logging.getLogger(__name__)

class IntegrityService:
    def __init__(self, db: Session):
        self.db = db

    async def detect_gaps(self, symbol: Optional[str] = None, days: int = 7) -> GapDiscoveryResponse:
        """
        Detect gaps in candle data for active symbols.
        Uses a SQL approach to find missing intervals.
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get active symbols and their timeframes
        query = self.db.query(MarketSymbol).filter(MarketSymbol.is_active == True)
        if symbol:
            query = query.filter(MarketSymbol.symbol == symbol)
        
        active_symbols = query.all()
        
        # Supported timeframes (could be dynamic from config)
        timeframes = ["M1", "M5", "M15", "H1", "H4", "D1"]
        tf_minutes = {
            "M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440
        }

        all_gaps = []
        summary = {}

        for ms in active_symbols:
            for tf in timeframes:
                interval_mins = tf_minutes.get(tf)
                if not interval_mins: continue

                # Professional SQL to find gaps:
                # 1. Generate a series of expected timestamps
                # 2. Left join with existing candles
                # 3. Identify contiguous blocks of NULLs
                
                sql = text(f"""
                    WITH expected_timestamps AS (
                        SELECT generate_series(
                            CAST(:start_date AS TIMESTAMP), 
                            CAST(now() AS TIMESTAMP), 
                            CAST((:interval || ' minutes') AS interval)
                        ) AS ts
                    ),
                    missing_points AS (
                        SELECT e.ts
                        FROM expected_timestamps e
                        LEFT JOIN candles c ON c.timestamp = e.ts 
                            AND c.market_symbol_id = :ms_id 
                            AND c.timeframe = :tf
                        WHERE c.id IS NULL
                    ),
                    gap_groups AS (
                        SELECT ts,
                               ts - (row_number() OVER (ORDER BY ts) * CAST((:interval || ' minutes') AS interval)) as grp
                        FROM missing_points
                    )
                    SELECT min(ts) as gap_start, max(ts) as gap_end, count(*) as missing_count
                    FROM gap_groups
                    GROUP BY grp
                    HAVING count(*) > 1  -- Only report significant gaps
                    ORDER BY gap_start DESC
                """)

                result = self.db.execute(sql, {
                    "start_date": start_date,
                    "interval": interval_mins,
                    "ms_id": ms.id,
                    "tf": tf
                }).fetchall()

                for row in result:
                    gap = GapInfo(
                        symbol=ms.symbol,
                        timeframe=tf,
                        gap_start=row.gap_start,
                        gap_end=row.gap_end,
                        missing_count=row.missing_count
                    )
                    all_gaps.append(gap)
                    
                    key = f"{ms.symbol}_{tf}"
                    summary[key] = summary.get(key, 0) + 1

        return GapDiscoveryResponse(
            total_gaps=len(all_gaps),
            summary=summary,
            gaps=all_gaps
        )

    async def trigger_auto_repair(self):
        """
        Scan for gaps and trigger backfill tasks.
        (To be called by a periodic job)
        """
        # ... logic to call backfill for each detected significant gap ...
        pass
