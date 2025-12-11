import sys
import os
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, func, case
from sqlalchemy.orm import sessionmaker
from app.models.trade import Trade, TradeStatus
from app.database import Base

# Assuming running from services/api-gateway locally against localhost DB
# If running in docker, this might need adjustment, but user said 'localhost/api/v1' implies they are hitting it from host
DATABASE_URL = "postgresql://trader:trader@localhost:5432/mtf_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def debug_query():
    db = SessionLocal()
    try:
        print("Testing query...")
        results = db.query(
            Trade.strategy_name,
            func.count(Trade.trade_id).label('total_trades'),
            func.sum(Trade.pnl_usd).label('total_pnl'),
            func.sum(case((Trade.pnl_usd > 0, 1), else_=0)).label('wins')
        ).filter(
            Trade.status == TradeStatus.CLOSED
        ).group_by(Trade.strategy_name).all()
        
        print("Query successful!")
        for r in results:
            print(f"Strategy: {r.strategy_name}, Trades: {r.total_trades}, PnL: {r.total_pnl}, Wins: {r.wins}")
            
    except Exception as e:
        print(f"Query failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_query()
