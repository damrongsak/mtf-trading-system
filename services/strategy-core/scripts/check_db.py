
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.saved_strategy import SavedStrategy
from app.models.deployment import Deployment

def check():
    db = SessionLocal()
    try:
        strategies = db.query(SavedStrategy).all()
        deployments = db.query(Deployment).all()
        
        print(f"--- DATABASE DUMP ---")
        print(f"Saved Strategies: {len(strategies)}")
        for s in strategies:
            print(f"  [{s.id}] {s.name}")
            
        print(f"Deployments: {len(deployments)}")
        for d in deployments:
            print(f"  [{d.id}] Strat: {d.strategy_id} | Symbol: {d.stock_symbol} | Status: {d.status}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check()
