
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
# Strategy Core might not have User model fully mapped or needed? 
# Usually Strategy Core focuses on execution. But Deployment links to User.
# Let's hope User model is available or we can just mock the ID if we query it differently.
# Check imports in strategy-core models.
try:
    from app.models.user import User
except ImportError:
    # Fallback: Define minimal User class or just skip user check if we can get ID from string
    from sqlalchemy import Column, String
    from sqlalchemy.dialects.postgresql import UUID
    from app.database import Base
    class User(Base):
        __tablename__ = "users"
        __table_args__ = {"extend_existing": True}
        id = Column(UUID(as_uuid=True), primary_key=True)
        username = Column(String)

# Configuration
STRATEGY_PATH = Path("/app/app/strategies/smc_v1/strategy.py") # Inside container: /app is workdir, so /app/app/... 
# Wait, WORKDIR is /app. So app/strategies...
# Local path: services/strategy-core/app/strategies/smc_v1/strategy.py
TARGET_SYMBOL = "XAU/USD"
TIMEFRAME = "M5" # Primary trigger timeframe (5min)
CAPITAL = 10000.0
RISK_PCT = 0.01

def activate_smc():
    db = SessionLocal()
    try:
        # 1. Get User
        # We try to query raw if User model implementation is partial
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
             user = db.query(User).first()
        
        if not user:
            print("ERROR: No user found. Create a user first.")
            return

        print(f"Using User: {user.username} ({user.id})")

        # 2. Read Strategy Code
        # Adjust path for container
        code_path = Path("app/strategies/smc_v1/strategy.py")
        
        if not code_path.exists():
            print(f"ERROR: Strategy file not found at {code_path}")
            # Try absolute
            code_path = Path("/app/app/strategies/smc_v1/strategy.py")
        
        if not code_path.exists():
             print(f"Still not found. Current CWD: {os.getcwd()}")
             # One last try
             code_path = Path("services/strategy-core/app/strategies/smc_v1/strategy.py")

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
            "description": "SMC V1: Macro(1H) + Setup(15m) + Trigger(5m)",
            "defaults": {
                "risk_per_trade": RISK_PCT,
                "tf_macro": "1h",
                "tf_setup": "15min"
            }
        }

        if saved_strat:
            print(f"Updating existing strategy '{strat_name}'...")
            saved_strat.code = code_content
            saved_strat.parameters = metadata["defaults"]
            # saved_strat.description = metadata["description"] # Field missing in strategy-core model
        else:
            print(f"Creating new strategy '{strat_name}'...")
            saved_strat = SavedStrategy(
                user_id=user.id,
                name=strat_name,
                # description=metadata["description"], # Field missing in strategy-core model
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
            print(f"Deployment already exists ({deployment.status}). ID: {deployment.id}", flush=True)
            if deployment.status != "ACTIVE":
                print("Re-activating deployment...", flush=True)
                deployment.status = "ACTIVE"
        else:
            print(f"Creating new ACTIVE deployment for {TARGET_SYMBOL}...", flush=True)
            deployment = Deployment(
                user_id=user.id,
                strategy_id=saved_strat.id,
                stock_symbol=TARGET_SYMBOL,
                timeframe=TIMEFRAME,
                config_snapshot=config_snapshot,
                status="ACTIVE",
                is_live=False # Paper Trading by default
            )
            print("Adding deployment to session...", flush=True)
            db.add(deployment)
        
        print("Committing transaction...", flush=True)
        db.commit()
        print("✅ SMC V1 Activated Successfully!", flush=True)
        print(f"Deployment ID: {deployment.id}", flush=True)
        print("Run 'docker compose restart strategy-core' to apply changes.", flush=True)

    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        print("Closing session...", flush=True)
        db.close()

if __name__ == "__main__":
    activate_smc()
