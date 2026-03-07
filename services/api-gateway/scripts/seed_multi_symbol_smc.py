import sys
import os
import uuid
import json
import logging
from sqlalchemy import text

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants from previous DB check
FUND_ID = "0b4fa6dd-da49-4e4f-8345-10d9271324cb"
CTRADER_ACC_ID = "ae8d4499-c90d-43f6-b14a-d5697dd4c799"
OANDA_ACC_ID = "53e48543-7f6f-465c-ac20-d23d2d2b5495"

def seed_strategies():
    db = SessionLocal()
    try:
        strategies = [
            {
                "id": str(uuid.uuid4()),
                "name": "SMC EURUSD Live Monitoring",
                "fund_id": FUND_ID,
                "broker_account_id": CTRADER_ACC_ID,
                "template_id": "smc_v1",
                "symbol": "EURUSD",
                "is_active": True
            },
            {
                "id": str(uuid.uuid4()),
                "name": "SMC GBPUSD Live Monitoring (Oanda)",
                "fund_id": FUND_ID,
                "broker_account_id": OANDA_ACC_ID,
                "template_id": "smc_v1",
                "symbol": "GBP_USD",
                "is_active": True
            }
        ]

        for s in strategies:
            # Check if exists by name/symbol
            exists = db.execute(
                text("SELECT id FROM strategies WHERE name = :name"),
                {"name": s["name"]}
            ).fetchone()

            if not exists:
                logger.info(f"Seeding strategy: {s['name']} ({s['symbol']})")
                db.execute(
                    text("""
                        INSERT INTO strategies (id, fund_id, name, broker_account_id, template_id, config_json, risk_settings, is_active)
                        VALUES (:id, :fund_id, :name, :broker_account_id, :template_id, :config_json, :risk_settings, :is_active)
                    """),
                    {
                        "id": s["id"],
                        "fund_id": s["fund_id"],
                        "name": s["name"],
                        "broker_account_id": s["broker_account_id"],
                        "template_id": s["template_id"],
                        "config_json": json.dumps({"symbol": s["symbol"], "tf_macro": "4h", "tf_setup": "1h"}),
                        "risk_settings": json.dumps({"risk_per_trade_usd": 10.0, "max_trades": 3}),
                        "is_active": s["is_active"]
                    }
                )
            else:
                logger.info(f"Strategy {s['name']} already exists.")

        db.commit()
        logger.info("Multi-symbol seeding completed.")
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_strategies()
