
import asyncio
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules if needed, but we'll use direct SQL for simplicity
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@postgres:5432/mtf_db")

def inspect_data():
    print(f"Connecting to DB: {DATABASE_URL}")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Check Distinct Symbols
        print("\n--- Distinct Contract Symbols ---")
        result = session.execute(text("SELECT DISTINCT contract_symbol FROM open_interest ORDER BY contract_symbol"))
        symbols = [row[0] for row in result]
        for s in symbols:
            print(f"- {s}")

        # 2. Check Sample Rows
        print("\n--- Sample Rows (Limit 5) ---")
        result = session.execute(text("SELECT contract_symbol, strike, call_oi, put_oi, snapshot_at FROM open_interest LIMIT 5"))
        for row in result:
            print(row)

        # 3. Check Count
        count = session.execute(text("SELECT COUNT(*) FROM open_interest")).scalar()
        print(f"\nTotal Records: {count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    inspect_data()
