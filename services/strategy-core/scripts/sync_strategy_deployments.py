import os
import sys
import uuid
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models.strategy import Strategy

STRATEGIES_DIR = Path(os.path.dirname(__file__)) / "../app/strategies"

def sync_deployments():
    db = SessionLocal()
    try:
        # 1. Get a Default Fund and Broker Account for System Strategies
        # In a real system, these would be 'System' or 'Demo' specific
        fund_row = db.execute(text("SELECT id FROM funds LIMIT 1")).fetchone()
        broker_row = db.execute(text("SELECT id FROM broker_accounts LIMIT 1")).fetchone()
        
        if not fund_row or not broker_row:
            print("❌ Error: Need at least one fund and one broker_account in DB to sync strategies.")
            return

        fund_id = fund_row[0]
        broker_account_id = broker_row[0]
        
        print(f"Using Fund: {fund_id}, Broker: {broker_account_id}")

        # 2. Scan Templates
        for strategy_dir in STRATEGIES_DIR.iterdir():
            if strategy_dir.is_dir() and (strategy_dir / "strategy.py").exists():
                template_id = strategy_dir.name
                
                # Check if deployment already exists for this template
                existing = db.query(Strategy).filter(Strategy.template_id == template_id).first()
                
                if not existing:
                    print(f"🚀 Registering new system deployment for: {template_id}")
                    new_strat = Strategy(
                        id=uuid.uuid4(),
                        fund_id=fund_id,
                        name=f"System: {template_id.replace('_', ' ').title()}",
                        template_id=template_id,
                        broker_account_id=broker_account_id,
                        config_json={}, # Default params from METADATA will be used by Fleet
                        is_active=False, # Sandbox mode by default
                        is_shadow=True   # Protection: default to shadow
                    )
                    db.add(new_strat)
                else:
                    print(f"✅ Template {template_id} already has a deployment record.")

        db.commit()
        print("🎉 Sync complete.")

    except Exception as e:
        print(f"❌ Error during sync: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    sync_deployments()
