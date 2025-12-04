import sys
import os

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from app.database import SessionLocal
from app.models.trade import Trade, TradeStatus

def check_trades():
    db = SessionLocal()
    try:
        total_trades = db.query(Trade).count()
        closed_trades = db.query(Trade).filter(Trade.status == TradeStatus.CLOSED).count()
        open_trades = db.query(Trade).filter(Trade.status == TradeStatus.OPEN).count()
        
        print(f"Total Trades: {total_trades}")
        print(f"Closed Trades: {closed_trades}")
        print(f"Open Trades: {open_trades}")
        
        if total_trades > 0:
            first_trade = db.query(Trade).first()
            print(f"First Trade: {first_trade}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_trades()
