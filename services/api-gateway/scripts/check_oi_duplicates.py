
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@postgres:5432/mtf_db")

def check_duplicates():
    print(f"Connecting to DB: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\n--- Checking for Duplicate OI Records ---")
        # Query to find duplicates based on usage context (contract, strike, snapshot)
        query = text("""
            SELECT contract_symbol, strike, snapshot_at, COUNT(*) as cnt
            FROM open_interest
            GROUP BY contract_symbol, strike, snapshot_at
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
            LIMIT 20
        """)
        
        results = session.execute(query).fetchall()
        
        if not results:
            print("✅ NO DUPLICATES FOUND.")
        else:
            print(f"❌ FOUND {len(results)} DUPLICATE GROUPS (Showing top 20):")
            for row in results:
                print(f"- Symbol: {row[0]}, Strike: {row[1]}, Time: {row[2]} | Count: {row[3]}")

        # Also check for potential "logical" duplicates (same contract/strike same DAY but different timestamp?)
        # This helps verify if multiple snapshots per day are causing confusion
        print("\n--- Checking Snapshots per Day per Contract ---")
        query_snapshots = text("""
            SELECT DATE(snapshot_at) as date, COUNT(DISTINCT snapshot_at) as snapshots
            FROM open_interest
            GROUP BY DATE(snapshot_at)
            ORDER BY date DESC
            LIMIT 10
        """)
        daily_snaps = session.execute(query_snapshots).fetchall()
        for row in daily_snaps:
             print(f"- Date: {row[0]} | Snapshots: {row[1]}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_duplicates()
