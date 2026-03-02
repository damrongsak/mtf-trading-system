import os
import sys
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

# Add app directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base
from app.models.open_interest import OpenInterest
from app.analysis.liquidity_profile import LiquidityProfileAnalyzer

# Database URL (from env or fallback)
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@postgresql:5432/mtf_db")

def verify_e2e():
    print(f"--- Starting E2E OI Verification (Live DB) ---")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        # 1. Fetch the latest snapshot timestamp
        latest_snapshot = db.query(OpenInterest.snapshot_at).order_by(desc(OpenInterest.snapshot_at)).first()
        if not latest_snapshot:
            print("❌ No Open Interest data found in database.")
            return
            
        snapshot_at = latest_snapshot[0]
        print(f"Targeting Latest Snapshot: {snapshot_at}")
        
        # 2. Fetch records for this snapshot
        records = db.query(OpenInterest).filter(OpenInterest.snapshot_at == snapshot_at).all()
        print(f"Fetched {len(records)} records from DB.")
        
        # 3. Convert to Analyzer format
        rec_dicts = []
        for r in records:
            rec_dicts.append({
                'contract_symbol': r.contract_symbol,
                'strike': float(r.strike),
                'call_oi': float(r.call_oi or 0),
                'put_oi': float(r.put_oi or 0),
                'underlying_price': float(r.underlying_price) if r.underlying_price else None,
                'dte': r.dte
            })
            
        # 4. Run Analyzer
        analyzer = LiquidityProfileAnalyzer()
        # Mocking spot price as 2005.0 or something close to Gold for testing
        current_spot = 2005.0 
        
        # We can try to guess the spot from the underlying prices if available
        underlyings = [r['underlying_price'] for r in rec_dicts if r['underlying_price']]
        if underlyings:
            # For testing purposes, we use a price near the first underlying
            current_spot = underlyings[0] * 0.998 # Slight discount for spot
            
        print(f"Using Mock Spot Price: {current_spot}")
        
        analysis = analyzer.analyze_snapshot(rec_dicts, current_spot_price=current_spot)
        
        if not analysis:
            print("❌ Analysis failed to produce results.")
            return
            
        print("\n--- E2E Analysis Results ---")
        print(f"Target Contract: {analysis['target_contract']}")
        print(f"Market Regime: {analysis['regime'].regime}")
        print(f"Max Pain Strike: {analysis['max_pain']}")
        
        print("\nKey Gamma Levels:")
        for lvl in analysis['levels']:
            print(f"- {lvl.type}: Strike {lvl.strike} (Mapped: {lvl.price:.2f}) | Significance: {lvl.significance_score:.2f}")
            
        print("\n✅ E2E Verification Successful!")
        
    except Exception as e:
        print(f"❌ E2E Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_e2e()
