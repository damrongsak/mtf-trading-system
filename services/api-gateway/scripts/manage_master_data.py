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
from app.models.deployment import Deployment
from app.models.user_fund import Fund, UserFund
from app.models.market import MarketCategory, MarketSymbol
from app.models.data_source import DataSource
from app.models.broker_account import BrokerAccount
from app.models.system_config import SystemConfig
from app.models.risk_rule import RiskRule
from app.models.risk_filter import RiskFilter
from app.models.plugins import Plugin, UserPlugin
from app.models.telegram_chat_mapping import TelegramChatMapping
from app.models.strategy import Strategy
from app.models.saved_strategy import SavedStrategy
from app.models.strategy_config import StrategyConfig
from app.models.prompt import SystemPrompt
from app.models.rag import LibraryBook
from app.models.api_key import ApiKey
from app.utils.crypto import decrypt_data, encrypt_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MDMS")

MASTER_DATA_DIR = "/master_data"

# Order matters for dependencies during import
TABLE_MODELS = [
    (User, "users.json"),
    (SystemConfig, "system_configs.json"),
    (SystemPrompt, "system_prompts.json"),
    (RiskRule, "risk_rules.json"),
    (RiskFilter, "risk_filters.json"),
    (MarketCategory, "market_categories.json"),
    (DataSource, "data_sources.json"),
    (Fund, "funds.json"),
    (UserFund, "user_funds.json"),
    (BrokerAccount, "broker_accounts.json"),
    (MarketSymbol, "market_symbols.json"),
    (Plugin, "plugins.json"),
    (UserPlugin, "user_plugins.json"),
    (TelegramChatMapping, "telegram_chat_mappings.json"),
    (SavedStrategy, "saved_strategies.json"),
    (StrategyConfig, "strategy_configs.json"),
    (Strategy, "strategies.json"),
    (Deployment, "deployments.json"),
    (LibraryBook, "library_books.json"),
    (ApiKey, "api_keys.json")
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
                
                # Sanitize sensitive fields in DataSources
                if model_class == DataSource and "config_json" in item_dict:
                    config = item_dict["config_json"]
                    # If encrypted, decrypt first so we can sanitize keys
                    try:
                        if isinstance(config, str):
                            config = decrypt_data(config)
                    except Exception:
                        pass
                        
                    if isinstance(config, dict):
                        provider = item_dict.get("provider", "UNKNOWN")
                        sensitive_keys = ["token", "client_secret", "refresh_token", "api_key", "password"]
                        for sk in sensitive_keys:
                            if sk in config:
                                # Standard prefixing for deployment reproducibility
                                env_suffix = sk.upper()
                                # Special case mapping for OANDA
                                if provider == "OANDA" and sk == "token":
                                    env_suffix = "API_KEY"
                                
                                config[sk] = f"SECRET_{provider.upper()}_{env_suffix}"
                        item_dict["config_json"] = config
                
                # Sanitize ApiKey secrets
                if model_class == ApiKey and item_dict.get("api_secret"):
                    item_dict["api_secret"] = "SECRET_API_SECRET"

                # Sanitize BrokerAccount credentials
                if model_class == BrokerAccount and "credentials_encrypted" in item_dict:
                    creds = item_dict["credentials_encrypted"]
                    try:
                        if isinstance(creds, str):
                            creds = decrypt_data(creds)
                    except Exception:
                        pass
                    
                    if isinstance(creds, dict):
                        # Simple sanitization for all keys starting with SECRET_ logic
                        # or just mask everything if it's sensitive
                        for sk in creds:
                            creds[sk] = f"SECRET_{item_dict.get('broker_name', 'BROKER').upper()}_{sk.upper()}"
                        item_dict["credentials_encrypted"] = creds

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
                        if key in pk_names:
                            continue
                            
                        # Special handling for JSONB fields with sanitization
                        if isinstance(value, dict) and key == "config_json" and model_class == DataSource:
                            # Force a new dictionary object to ensure SQLAlchemy detects the change
                            existing_config = getattr(existing, key) or {}
                            # If encrypted string, decrypt first so we can update as a dict
                            if isinstance(existing_config, str):
                                try:
                                    existing_config = decrypt_data(existing_config)
                                except Exception:
                                    existing_config = {}
                            
                            temp_config = dict(existing_config)
                            for sub_key, sub_val in value.items():
                                # Only update if it's not a placeholder
                                if isinstance(sub_val, str) and sub_val.startswith("SECRET_"):
                                    # Try to recover from ENV
                                    env_key = sub_val.replace("SECRET_", "")
                                    env_val = os.getenv(env_key)
                                    if env_val:
                                        temp_config[sub_key] = env_val
                                    else:
                                        provider = item_dict.get("provider", "UNKNOWN")
                                        logger.warning(f"  - [SKIP] Could not resolve {env_key} from ENV for {provider}. Keeping placeholder.")
                                        temp_config[sub_key] = sub_val
                                else:
                                    temp_config[sub_key] = sub_val
                            
                            # [ENCRYPTION-ENFORCEMENT] Encrypt before saving
                            setattr(existing, key, encrypt_data(temp_config))
                        elif model_class == ApiKey and key == "api_secret" and isinstance(value, str) and value.startswith("SECRET_"):
                            env_val = os.getenv(value.replace("SECRET_", ""))
                            if env_val:
                                setattr(existing, key, encrypt_data(env_val))
                        elif model_class == BrokerAccount and key == "credentials_encrypted" and isinstance(value, dict):
                            # Resolve placeholders for credentials
                            temp_creds = dict(getattr(existing, key) or {})
                            for sk, sv in value.items():
                                if isinstance(sv, str) and sv.startswith("SECRET_"):
                                    ev = os.getenv(sv.replace("SECRET_", ""))
                                    if ev: temp_creds[sk] = ev
                                    else: temp_creds[sk] = sv
                                else:
                                    temp_creds[sk] = sv
                            setattr(existing, key, encrypt_data(temp_creds))
                        else:
                            setattr(existing, key, value)
                else:
                    # Insert
                    # Resolve placeholders from ENV before inserting
                    if "config_json" in item_dict and isinstance(item_dict["config_json"], dict):
                        for sub_key, sub_val in item_dict["config_json"].items():
                            if isinstance(sub_val, str) and sub_val.startswith("SECRET_"):
                                env_key = sub_val.replace("SECRET_", "")
                                env_val = os.getenv(env_key)
                                if env_val:
                                    item_dict["config_json"][sub_key] = env_val
                                else:
                                    provider = item_dict.get("provider", "UNKNOWN")
                                    logger.warning(f"  - [SKIP] Could not resolve {env_key} from ENV for {provider} during insert. Keeping placeholder.")
                    
                    if "credentials_encrypted" in item_dict and isinstance(item_dict["credentials_encrypted"], dict):
                        for sub_key, sub_val in item_dict["credentials_encrypted"].items():
                            if isinstance(sub_val, str) and sub_val.startswith("SECRET_"):
                                env_key = sub_val.replace("SECRET_", "")
                                env_val = os.getenv(env_key)
                                if env_val:
                                    item_dict["credentials_encrypted"][sub_key] = env_val
                    
                    if "api_secret" in item_dict and isinstance(item_dict["api_secret"], str) and item_dict["api_secret"].startswith("SECRET_"):
                         env_val = os.getenv(item_dict["api_secret"].replace("SECRET_", ""))
                         if env_val:
                             item_dict["api_secret"] = env_val

                    # [ENCRYPTION-ENFORCEMENT] Encrypt sensitive fields before creating model instance
                    if model_class == DataSource and "config_json" in item_dict:
                        item_dict["config_json"] = encrypt_data(item_dict["config_json"])
                    
                    if model_class == BrokerAccount and "credentials_encrypted" in item_dict:
                        item_dict["credentials_encrypted"] = encrypt_data(item_dict["credentials_encrypted"])
                    
                    if model_class == ApiKey and "api_secret" in item_dict:
                        item_dict["api_secret"] = encrypt_data(item_dict["api_secret"])

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
