import os
import sys
import uuid
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

sys.path.append("/app")
from app.database import engine
from app.models import User, BrokerAccount, DataSource
from app.models.user_fund import Fund, UserFund
from app.utils.crypto import encrypt_data
from app.security import get_password_hash

load_dotenv()

def setup_demo_test():
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        print("Setting up demo1 and cTrader demo account...")
        
        # 1. Create User demo1
        username = "demo1"
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if not user:
            print(f"Creating user {username}...")
            user = User(
                username=username,
                email="demo1@example.com",
                password_hash=get_password_hash("password123"),
                is_active=True
            )
            db.add(user)
            db.flush()
        else:
            print(f"User {username} already exists. Updating password...")
            user.password_hash = get_password_hash("password123")

        # 2. Create Fund
        fund_name = "Demo Full System Test Fund"
        fund = db.execute(select(Fund).join(UserFund).where(UserFund.user_id == user.id, Fund.name == fund_name)).scalar_one_or_none()
        if not fund:
            print(f"Creating fund '{fund_name}'...")
            fund = Fund(
                name=fund_name,
                description="Demo Fund for Full System Test",
                strategy_type="MTF_SMC_BASIC",
                max_risk_per_trade=100.0,
                risk_percentage=0.01
            )
            db.add(fund)
            db.flush()
            
            user_fund = UserFund(user_id=user.id, fund_id=fund.id, role="OWNER")
            db.add(user_fund)
            db.flush()
        else:
            print(f"Fund '{fund_name}' already exists.")

        # 3. Create cTrader Demo Account
        raw_creds = {
            "host": "demo.ctraderapi.com",
            "port": 5035,
            "account_id": "9919680",
            "client_id": "20383_R8XWLegmMzooUUNZ1BbrBiWXCrlypf1ucGPd5ioaQaptQLsY8B",
            "client_secret": "Ba7u0sGyBKrGjzIC3jYMvLGqBQP6q2ofYiE4pFy1BPQtG6GFFW",
            "token": "EA0tpIDJ6rLLDWtri3fjF8JqvxNzjHQ9VwBkVFSQHAM",
            "refresh_token": "-pc0XXvC21HbsrWpHc61GUGaT8kkB-irA1XaT-8IxWw",
            "expires_at": 1773313483
        }
        enc_creds = encrypt_data(raw_creds)

        acc = db.execute(select(BrokerAccount).where(BrokerAccount.fund_id == fund.id, BrokerAccount.broker_name == "CTRADER")).scalar_one_or_none()
        if not acc:
            print("Creating cTrader Demo BrokerAccount...")
            acc = BrokerAccount(
                id=uuid.uuid4(),
                fund_id=fund.id,
                broker_name="CTRADER",
                account_name="cTrader Demo System Test",
                account_number="9919680",
                credentials_encrypted=enc_creds,
                is_live=False,
                is_active=True,
                environment="demo",
                supported_symbols=["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
            )
            db.add(acc)
        else:
            print("cTrader Demo BrokerAccount already exists. Updating credentials...")
            acc.credentials_encrypted = enc_creds
            acc.environment = "demo"
            acc.is_live = False
            acc.is_active = True
            acc.account_number = "9919680"

        # Ensure cTrader Data Source is active
        ds = db.execute(select(DataSource).where(DataSource.provider == "CTRADER")).scalar_one_or_none()
        if ds:
            print("Ensuring cTrader DataSource is active")
            ds.is_active = True
        else:
            print("cTrader DataSource not found. Creating one...")
            ds = DataSource(
                name="CTRADER",
                provider="CTRADER",
                type="api",
                config_json={},
                is_active=True
            )
            db.add(ds)
        
        db.commit()
        print("✅ Demo setup completed successfully!")
        print(f"User: {username}")
        print(f"Fund: {fund_name}")
        print(f"Broker Account: {acc.account_name} ({acc.account_number})")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during setup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_demo_test()
