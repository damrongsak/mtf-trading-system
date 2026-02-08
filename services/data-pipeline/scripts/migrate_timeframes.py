#!/usr/bin/env python3
"""
Database migration script to update timeframe format from non-standard to cTrader standard.
Converts: D -> D1, W -> W1, M -> MN1
"""

import sys
import os
from sqlalchemy import text

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.database import SessionLocal

def migrate_timeframes():
    """Update existing candle records to use standard timeframe format."""
    db = SessionLocal()
    
    try:
        print("Starting timeframe migration...")
        
        # Update D -> D1
        result = db.execute(text("UPDATE candles SET timeframe = 'D1' WHERE timeframe = 'D'"))
        d_count = result.rowcount
        print(f"✓ Updated {d_count} Daily candles: D -> D1")
        
        # Update W -> W1
        result = db.execute(text("UPDATE candles SET timeframe = 'W1' WHERE timeframe = 'W'"))
        w_count = result.rowcount
        print(f"✓ Updated {w_count} Weekly candles: W -> W1")
        
        # Update M -> MN1
        result = db.execute(text("UPDATE candles SET timeframe = 'MN1' WHERE timeframe = 'M'"))
        m_count = result.rowcount
        print(f"✓ Updated {m_count} Monthly candles: M -> MN1")
        
        db.commit()
        
        total = d_count + w_count + m_count
        print(f"\n✅ Migration complete! Updated {total} total records.")
        
        # Verify
        print("\nVerifying migration...")
        result = db.execute(text("SELECT DISTINCT timeframe FROM candles ORDER BY timeframe"))
        timeframes = [row[0] for row in result]
        print(f"Current timeframes in database: {', '.join(timeframes)}")
        
        # Check for old formats
        old_formats = [tf for tf in timeframes if tf in ['D', 'W', 'M']]
        if old_formats:
            print(f"⚠️  WARNING: Old formats still present: {', '.join(old_formats)}")
        else:
            print("✓ No old formats detected")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_timeframes()
