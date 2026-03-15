import sys
import os
import json
import logging
import argparse
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal
from app.models.user import User
from app.models.user_fund import Fund, UserFund
from app.models.market import MarketCategory, MarketSymbol
from app.models.data_source import DataSource
from app.models.broker_account import BrokerAccount
from app.models.system_config import SystemConfig
from app.models.risk_rule import RiskRule
from app.models.plugins import Plugin, UserPlugin
from app.models.telegram_chat_mapping import TelegramChatMapping

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MDMS")

MASTER_DATA_DIR = "/master_data"

# Order matters for dependencies during import
TABLE_MODELS = [
    (SystemConfig, "system_configs.json"),
    (RiskRule, "risk_rules.json"),
    (MarketCategory, "market_categories.json"),
    (DataSource, "data_sources.json"),
    (User, "users.json"),
    (Fund, "funds.json"),
    (UserFund, "user_funds.json"),
    (BrokerAccount, "broker_accounts.json"),
    (MarketSymbol, "market_symbols.json"),
    (Plugin, "plugins.json"),
    (UserPlugin, "user_plugins.json"),
    (TelegramChatMapping, "telegram_chat_mappings.json")
]

from enum import Enum

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

def export_data():
    logger.info(f"Starting export to {MASTER_DATA_DIR}...")
    if not os.path.exists(MASTER_DATA_DIR):
        os.makedirs(MASTER_DATA_DIR)

    db = SessionLocal()
    try:
        for model_class, filename in TABLE_MODELS:
            logger.info(f"Exporting {model_class.__name__}...")
            items = db.query(model_class).all()
            
            data = []
            for item in items:
                # Convert model instance to dict
                columns = [c.key for c in inspect(item).mapper.column_attrs]
                item_dict = {c: getattr(item, c) for c in columns}
                data.append(item_dict)
            
            filepath = os.path.join(MASTER_DATA_DIR, filename)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, cls=CustomEncoder)
            logger.info(f"  - Saved {len(data)} records to {filename}")
            
        logger.info("✅ Export completed successfully.")
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        raise
    finally:
        db.close()

def import_data():
    logger.info(f"Starting import from {MASTER_DATA_DIR}...")
    if not os.path.exists(MASTER_DATA_DIR):
        logger.error(f"Master data directory {MASTER_DATA_DIR} does not exist.")
        return

    db = SessionLocal()
    try:
        # We process in order to respect foreign keys
        for model_class, filename in TABLE_MODELS:
            filepath = os.path.join(MASTER_DATA_DIR, filename)
            if not os.path.exists(filepath):
                logger.warning(f"  - File {filename} not found, skipping.")
                continue

            with open(filepath, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Importing {len(data)} records for {model_class.__name__}...")
            
            # Determine primary key column(s)
            pk_names = [pk.name for pk in inspect(model_class).primary_key]
            
            for item_dict in data:
                # Build filter for primary key
                pk_filter = {pk: item_dict[pk] for pk in pk_names}
                
                # Check if exists
                existing = db.query(model_class).filter_by(**pk_filter).first()
                
                if existing:
                    # Update
                    for key, value in item_dict.items():
                        if key not in pk_names:
                            setattr(existing, key, value)
                else:
                    # Insert
                    new_item = model_class(**item_dict)
                    db.add(new_item)
            
            db.commit()
            logger.info(f"  - Finished {model_class.__name__}")
            
        logger.info("✅ Import completed successfully.")
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master Data Management System")
    parser.add_argument("action", choices=["export", "import"], help="Action to perform")
    
    args = parser.parse_args()
    
    if args.action == "export":
        export_data()
    elif args.action == "import":
        import_data()
