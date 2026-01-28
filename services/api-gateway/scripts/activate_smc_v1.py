
import os
import sys
import uuid
import json
from pathlib import Path

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import SessionLocal
from app.models.saved_strategy import SavedStrategy
from app.models.deployment import Deployment
from app.models.user import User

# Configuration
STRATEGY_PATH = Path("/app/services/strategy-core/app/strategies/smc_v1/strategy.py")
# For local running (outside docker or if paths differ), try relative path if absolute fails
LOCAL_STRATEGY_PATH = Path("../strategy-core/app/strategies/smc_v1/strategy.py")

TARGET_SYMBOL = "XAU/USD"
TIMEFRAME = "M15" # Primary trigger timeframe
CAPITAL = 10000.0
RISK_PCT = 0.01

def activate_smc():
    db = SessionLocal()
    try:
        # 1. Get User
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            user = db.query(User).first()
        
        if not user:
            print("ERROR: No user found. Create a user first.")
            return

        print(f"Using User: {user.username} ({user.id})")

        # 2. Read Strategy Code
        code_path = STRATEGY_PATH if STRATEGY_PATH.exists() else LOCAL_STRATEGY_PATH
        if not code_path.exists():
             # Try resolving from current script loc
             code_path = Path(__file__).parent.parent.parent / "strategy-core/app/strategies/smc_v1/strategy.py"
        
        if not code_path.exists():
            print(f"ERROR: Strategy file not found at {code_path}")
            return
            
        with open(code_path, "r") as f:
            code_content = f.read()

        print(f"Read {len(code_content)} bytes from {code_path}")

        # 3. Create or Update SavedStrategy
        strat_name = "Smart Money Concepts V1"
        saved_strat = db.query(SavedStrategy).filter(
            SavedStrategy.name == strat_name,
            SavedStrategy.user_id == user.id
        ).first()

        metadata = {
            "name": strat_name,
            "description": "SMC V1: Macro Bias (H4) + Setup Zone (H1) + Trigger (M15)",
            "defaults": {
                "risk_per_trade": RISK_PCT
            }
        }

        if saved_strat:
            print(f"Updating existing strategy '{strat_name}'...")
            saved_strat.code = code_content
            saved_strat.parameters = metadata["defaults"]
            saved_strat.description = metadata["description"]
        else:
            print(f"Creating new strategy '{strat_name}'...")
            saved_strat = SavedStrategy(
                user_id=user.id,
                name=strat_name,
                description=metadata["description"],
                code=code_content,
                is_public=True,
                parameters=metadata["defaults"]
            )
            db.add(saved_strat)
            db.flush() # Get ID

        print(f"Strategy ID: {saved_strat.id}")

        # 4. Create Active Deployment
        # Check if active deployment exists
        deployment = db.query(Deployment).filter(
            Deployment.strategy_id == saved_strat.id,
            Deployment.stock_symbol == TARGET_SYMBOL,
            Deployment.status.in_(["ACTIVE", "STARTING"])
        ).first()

        config_snapshot = {
            "capital": CAPITAL,
            "risk_pct": RISK_PCT,
            "strategy_params": {}
        }

        if deployment:
            print(f"Deployment already exists ({deployment.status}). ID: {deployment.id}")
            if deployment.status != "ACTIVE":
                print("Re-activating deployment...")
                deployment.status = "ACTIVE"
        else:
            print(f"Creating new ACTIVE deployment for {TARGET_SYMBOL}...")
            deployment = Deployment(
                user_id=user.id,
                strategy_id=saved_strat.id,
                stock_symbol=TARGET_SYMBOL,
                timeframe=TIMEFRAME,
                config_snapshot=config_snapshot,
                status="ACTIVE",
                is_live=False # Paper Trading by default
            )
            db.add(deployment)
        
        db.commit()
        print("✅ SMC V1 Activated Successfully!")
        print(f"Deployment ID: {deployment.id}")
        print("Run 'docker compose restart strategy-core' to apply changes.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    activate_smc()
