import sys
import os
import uuid
import json
import logging
import asyncio
from datetime import datetime, timezone
from decimal import Decimal

# Add parent directory to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.models.user_fund import Fund, UserFund, UserRole
from app.models.market import MarketCategory, MarketSymbol
from app.models.data_source import DataSource
from app.models.broker_account import BrokerAccount
from app.models.system_config import SystemConfig
from app.models.risk_rule import RiskRule, RuleType
from app.security import get_password_hash
from app.utils.crypto import encrypt_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset_database():
    logger.info("Dropping and recreating public schema...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()
    logger.info("Database reset complete.")

def seed_system_configs(db):
    logger.info("Seeding System Configs...")
    configs = {
        "supported_timeframes": (["M1", "M5", "M15", "H1", "H4", "D1", "W1", "MN1"], "Default supported timeframes")
    }
    for key, (value, desc) in configs.items():
        exists = db.query(SystemConfig).filter(SystemConfig.key == key).first()
        if not exists:
            config = SystemConfig(
                key=key,
                value=value,
                description=desc
            )
            db.add(config)
        else:
            exists.value = value
            db.add(exists)
    db.commit()

def seed_users_and_funds(db):
    logger.info("Seeding Users and Funds...")
    
    # Create Default Fund
    fund = db.query(Fund).filter(Fund.name == "Olympus Master Fund").first()
    if not fund:
        fund = Fund(
            name="Olympus Master Fund",
            description="Main Production Trading Fund"
        )
        db.add(fund)
        db.flush()

    # Create Admin
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            email="admin@mtf-olympus.com",
            password_hash=get_password_hash("admin123"),
            is_active=True
        )
        db.add(admin)
        db.flush()

    # Create trader1 (cTrader)
    trader1 = db.query(User).filter(User.username == "trader1").first()
    if not trader1:
        trader1 = User(
            username="trader1",
            email="trader1@mtf-olympus.com",
            password_hash=get_password_hash("password123"),
            is_active=True
        )
        db.add(trader1)
        db.flush()

    # Create trader2 (Oanda)
    trader2 = db.query(User).filter(User.username == "trader2").first()
    if not trader2:
        trader2 = User(
            username="trader2",
            email="trader2@mtf-olympus.com",
            password_hash=get_password_hash("password123"),
            is_active=True
        )
        db.add(trader2)
        db.flush()

    # Create system user for internal service auth
    system_user_name = os.getenv("SYSTEM_USER", "execution_service")
    system_user_pass = os.getenv("SYSTEM_PASSWORD", "servicepassword123")
    system_user = db.query(User).filter(User.username == system_user_name).first()
    if not system_user:
        system_user = User(
            username=system_user_name,
            email=f"{system_user_name}@mtf-olympus.internal",
            password_hash=get_password_hash(system_user_pass),
            is_active=True,
            is_superuser=True
        )
        db.add(system_user)
        db.flush()

    # Assign to Fund
    for u, role in [(admin, UserRole.OWNER), (trader1, UserRole.TRADER), (trader2, UserRole.TRADER), (system_user, UserRole.MANAGER)]:
        exists = db.query(UserFund).filter(UserFund.user_id == u.id, UserFund.fund_id == fund.id).first()
        if not exists:
            db.add(UserFund(user_id=u.id, fund_id=fund.id, role=role))
    
    db.commit()
    return fund, trader1, trader2

def seed_market_data(db):
    logger.info("Seeding Market Data Categories, Sources and Symbols...")
    
    # Categories
    forex = db.query(MarketCategory).filter(MarketCategory.name == "Forex").first()
    if not forex:
        forex = MarketCategory(name="Forex", order_index=0)
        db.add(forex)
    
    metals = db.query(MarketCategory).filter(MarketCategory.name == "Metals").first()
    if not metals:
        metals = MarketCategory(name="Metals", order_index=1)
        db.add(metals)
    
    db.flush()

    # Data Sources
    oanda_ds = db.query(DataSource).filter(DataSource.name == "OANDA").first()
    if not oanda_ds:
        oanda_ds = DataSource(
            name="OANDA",
            provider="OANDA",
            type="api",
            config_json={
                "token": os.getenv("OANDA_API_KEY"),
                "account_id": os.getenv("OANDA_ACCOUNT_ID"),
                "environment": os.getenv("OANDA_ENV", "live")
            },
            is_active=True
        )
        db.add(oanda_ds)

    ctrader_ds = db.query(DataSource).filter(DataSource.name == "CTRADER").first()
    if not ctrader_ds:
        ctrader_ds = DataSource(
            name="CTRADER",
            provider="CTRADER",
            type="api",
            config_json={
                "host": "live.ctraderapi.com",
                "port": 5035,
                "account_id": "40816494",
                "client_id": os.getenv("CTRADER_CLIENT_ID"),
                "client_secret": os.getenv("CTRADER_CLIENT_SECRET"),
                "token": os.getenv("CTRADER_TOKEN"),
                "refresh_token": os.getenv("CTRADER_REFRESH_TOKEN")
            },
            is_active=True
        )
        db.add(ctrader_ds)
    db.flush()

    # Symbols for OANDA
    for s in ["XAU_USD", "EUR_USD", "GBP_USD"]:
        exists = db.query(MarketSymbol).filter(MarketSymbol.symbol == s, MarketSymbol.data_source_id == oanda_ds.id).first()
        if not exists:
            db.add(MarketSymbol(
                category_id=metals.id if "XAU" in s else forex.id,
                data_source_id=oanda_ds.id,
                symbol=s,
                display_name=s.replace("_", "/"),
                is_active=True
            ))

    # Symbols for CTRADER
    ctrader_symbols = {
        "XAUUSD": {"symbol_id": 1, "lot_size": 10000000},
        "EURUSD": {"symbol_id": 2, "lot_size": 10000000}
    }
    
    for s, details in ctrader_symbols.items():
        exists = db.query(MarketSymbol).filter(MarketSymbol.symbol == s, MarketSymbol.data_source_id == ctrader_ds.id).first()
        if not exists:
            db.add(MarketSymbol(
                category_id=metals.id if "XAU" in s else forex.id,
                data_source_id=ctrader_ds.id,
                symbol=s,
                display_name=s[:3] + "/" + s[3:],
                is_active=True,
                details=details
            ))
        else:
            # Update details if they changed
            exists.details = details
            db.add(exists)

    db.commit()

def seed_broker_accounts(db, fund, trader1, trader2):
    logger.info("Seeding Broker Accounts with encrypted credentials...")
    
    # cTrader for trader1
    ctrader_creds = {
        "host": "live.ctraderapi.com",
        "port": 5035,
        "account_id": "40816494",
        "client_id": os.getenv("CTRADER_CLIENT_ID"),
        "client_secret": os.getenv("CTRADER_CLIENT_SECRET"),
        "token": os.getenv("CTRADER_TOKEN"),
        "refresh_token": os.getenv("CTRADER_REFRESH_TOKEN"),
        "expires_at": 1773313483
    }
    
    exists_ctrader = db.query(BrokerAccount).filter(BrokerAccount.account_number == "40816494").first()
    if not exists_ctrader:
        db.add(BrokerAccount(
            fund_id=fund.id,
            broker_name="CTRADER",
            account_name="cTrader Live 40816494",
            account_number="40816494",
            credentials_encrypted=encrypt_data(ctrader_creds),
            is_active=True,
            is_live=True,
            environment="live",
            supported_symbols=["XAUUSD", "EURUSD"]
        ))
    else:
        exists_ctrader.credentials_encrypted = encrypt_data(ctrader_creds)
        db.add(exists_ctrader)

    # OANDA for trader2
    oanda_creds = {
        "api_key": os.getenv("OANDA_API_KEY"),
        "account_id": os.getenv("OANDA_ACCOUNT_ID"),
        "environment": "live"
    }

    oanda_acc_num = os.getenv("OANDA_ACCOUNT_ID")
    exists_oanda = db.query(BrokerAccount).filter(BrokerAccount.account_number == oanda_acc_num).first()
    if not exists_oanda:
        db.add(BrokerAccount(
            fund_id=fund.id,
            broker_name="OANDA",
            account_name="OANDA Live Main",
            account_number=oanda_acc_num,
            credentials_encrypted=encrypt_data(oanda_creds),
            is_active=True,
            is_live=True,
            environment="live",
            supported_symbols=["XAU_USD", "EUR_USD"]
        ))
    else:
        exists_oanda.credentials_encrypted = encrypt_data(oanda_creds)
        db.add(exists_oanda)
    
    db.commit()

def seed_risk_rules(db):
    logger.info("Seeding Risk Rules...")
    rules_data = [
        ("MAX_RISK_PER_TRADE_PRICE", RuleType.RISK_CAP, Decimal("10.00"), "USD", "Maximum risk in USD per trade (Basic Stage)"),
        ("MAX_RISK_PERCENTAGE", RuleType.RISK_CAP, Decimal("1.00"), "PERCENT", "Maximum risk as percentage of NAV per trade"),
        ("MIN_RR_RATIO", RuleType.RR_RATIO, Decimal("1.50"), "RATIO", "Minimum Risk-to-Reward ratio"),
        ("MIN_LOT_SIZE", RuleType.LOT_SIZE, Decimal("0.01"), "LOT", "Minimum allowable lot size")
    ]
    for name, rtype, val, unit, desc in rules_data:
        exists = db.query(RiskRule).filter(RiskRule.rule_name == name).first()
        if not exists:
            db.add(RiskRule(
                rule_name=name,
                rule_type=rtype,
                threshold_value=val,
                threshold_unit=unit,
                description=desc
            ))
    db.commit()

async def main():
    logger.info("Starting Production Initialization...")
    
    # Optional Reset
    if "--reset" in sys.argv:
        await reset_database()
    
    # Run AlembicMigrations via shell
    # NOTE: In a Docker environment, migrations must be run from the data-pipeline container.
    # This script will assume migrations have already been applied if --reset is not called,
    # or will simply proceed to seeding.
    logger.info("Skipping internal migrations. Ensure 'alembic upgrade head' is run from the data-pipeline container.")
    
    db = SessionLocal()
    try:
        seed_system_configs(db)
        fund, trader1, trader2 = seed_users_and_funds(db)
        seed_market_data(db)
        seed_broker_accounts(db, fund, trader1, trader2)
        seed_risk_rules(db)
        logger.info("Production Initialization Successful.")
    except Exception as e:
        logger.error(f"Initialization Failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
