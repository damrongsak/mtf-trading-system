
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@postgres:5432/mtf_db")

def verify_total_oi():
    print(f"Connecting to DB: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    target_date = "2026-02-10"

    try:
        print(f"\n--- Verifying Total OI for {target_date} ---")
        
        # Query to sum call_oi and put_oi for the specific date
        # We assume snapshot_at is a timestamp, so we cast to date or checking range might be safer if time is non-zero
        # Based on previous context, snapshot_at seems to be midnight
        
        query = text("""
            SELECT 
                SUM(COALESCE(call_oi, 0)) as total_call, 
                SUM(COALESCE(put_oi, 0)) as total_put,
                COUNT(*) as records
            FROM open_interest 
            WHERE DATE(snapshot_at) = :date
        """)
        
        result = session.execute(query, {"date": target_date}).fetchone()
        
        if result:
            total_call = float(result[0] or 0)
            total_put = float(result[1] or 0)
            grand_total = total_call + total_put
            records = result[2]
            
            print(f"Records Found: {records}")
            print(f"Total Call OI: {total_call:,.2f}")
            print(f"Total Put OI:  {total_put:,.2f}")
            print(f"Grand Total:   {grand_total:,.2f}")
            
            target_val = 899547.00
            diff = abs(grand_total - target_val)
            
            if diff < 1.0:
                print(f"\n✅ MATCH CONFIRMED: {grand_total:,.2f} == {target_val:,.2f}")
            else:
                print(f"\n❌ MISMATCH: DB has {grand_total:,.2f}, Expected {target_val:,.2f} (Diff: {diff:,.2f})")
                
                # Dig deeper if mismatch
                print("\nChecking distinct symbols breakdown:")
                breakdown = session.execute(text("""
                    SELECT 
                        contract_symbol, 
                        SUM(COALESCE(call_oi, 0) + COALESCE(put_oi, 0)) as total 
                    FROM open_interest 
                    WHERE DATE(snapshot_at) = :date 
                    GROUP BY contract_symbol 
                    ORDER BY total DESC
                """), {"date": target_date})
                
                for row in breakdown:
                    print(f"- {row[0]}: {float(row[1]):,.2f}")

        else:
            print("No data found for this date.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    verify_total_oi()
