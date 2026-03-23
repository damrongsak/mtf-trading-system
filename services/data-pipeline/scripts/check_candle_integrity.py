
import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta

# Ensure app is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal
from app.services.integrity_service import IntegrityService
from app.models.market import MarketSymbol

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("IntegrityCheck")

async def check_integrity():
    db = SessionLocal()
    try:
        service = IntegrityService(db)
        
        # Check last 30 days
        days = 30
        logger.info(f"Checking candle integrity for the last {days} days...")
        
        # Get active symbols to report status for each
        active_symbols = db.query(MarketSymbol).filter(MarketSymbol.is_active == True).all()
        if not active_symbols:
            logger.warning("No active symbols found in database.")
            return

        for ms in active_symbols:
            logger.info(f"Analyzing {ms.symbol} (ID: {ms.id})...")
            
        result = await service.detect_gaps(days=days)
        
        print("\n" + "="*50)
        print("CANDLE INTEGRITY REPORT")
        print("="*50)
        print(f"Total Gaps Found: {result.total_gaps}")
        
        if result.summary:
            print("\nSummary by Symbol_Timeframe:")
            for key, count in result.summary.items():
                print(f"  - {key}: {count} gaps")
        
        if result.gaps:
            print("\nTop 20 Detailed Gaps:")
            # Sort by gap_start descending
            sorted_gaps = sorted(result.gaps, key=lambda x: x.gap_start, reverse=True)
            for i, gap in enumerate(sorted_gaps[:20]):
                duration = gap.gap_end - gap.gap_start
                print(f"  {i+1}. {gap.symbol} {gap.timeframe} | {gap.gap_start} to {gap.gap_end} | Count: {gap.missing_count} | Duration: {duration}")
        
        print("="*50 + "\n")

    except Exception as e:
        logger.error(f"Error during integrity check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(check_integrity())
