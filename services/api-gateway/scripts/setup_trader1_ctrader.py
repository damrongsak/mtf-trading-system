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

def setup_trader1_ctrader():
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        print("Setting up trader1 and cTrader account...")
        
        # 1. Create User
        user = db.execute(select(User).where(User.username == "trader1")).scalar_one_or_none()
        if not user:
            print("Creating user trader1...")
            user = User(
                username="trader1",
                email="trader1@example.com",
                password_hash=get_password_hash("password123"),
                is_active=True
            )
            db.add(user)
            db.flush()
        else:
            print("User trader1 already exists.")
            # Ensure password is correct for testing
            user.password_hash = get_password_hash("password123")

        # 2. Create Fund
        fund_name = "Trader1 cTrader Fund"
        fund = db.execute(select(Fund).join(UserFund).where(UserFund.user_id == user.id, Fund.name == fund_name)).scalar_one_or_none()
        if not fund:
            print("Creating fund...")
            fund = Fund(
                name=fund_name,
                description="cTrader Live Testing Fund",
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
            print("Fund already exists.")

        # 3. Create cTrader Account
        client_id = "20383_R8XWLegmMzooUUNZ1BbrBiWXCrlypf1ucGPd5ioaQaptQLsY8B"
        client_secret = "Ba7u0sGyBKrGjzIC3jYMvLGqBQP6q2ofYiE4pFy1BPQtG6GFFW"
        account_id = "40816494"
        token = "SLGtuhJK9DdVQWZ6ObBFp_BTuy6kViaAgJwUpw2fI8o"
        refresh_token = "v3EdQvOC7plOofwfH5KEq8FL-vS-3LkzAZnxJapY-T0"

        raw_creds = {
            "client_id": client_id,
            "client_secret": client_secret,
            "account_id": account_id,
            "token": token,
            "refresh_token": refresh_token,
            "host": "live.ctraderapi.com"
        }
        enc_creds = encrypt_data(raw_creds)

        acc = db.execute(select(BrokerAccount).where(BrokerAccount.fund_id == fund.id, BrokerAccount.broker_name == "CTRADER")).scalar_one_or_none()
        if not acc:
            print("Creating cTrader BrokerAccount...")
            acc = BrokerAccount(
                id=uuid.uuid4(),
                fund_id=fund.id,
                broker_name="CTRADER",
                account_name="Trader1 cTrader Live",
                account_number=account_id or "Demo1",
                credentials_encrypted=enc_creds,
                is_live=True,
                is_active=True,
                environment="live",
                supported_symbols=["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
            )
            db.add(acc)
        else:
            print("cTrader BrokerAccount already exists. Updating credentials and environment...")
            acc.credentials_encrypted = enc_creds
            acc.environment = "live"
            acc.is_live = True
            acc.is_active = True
            acc.supported_symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]

        # Make Data Source Live
        ds = db.execute(select(DataSource).where(DataSource.provider == "CTRADER")).scalar_one_or_none()
        if ds:
            print("Ensuring cTrader DataSource is active")
            ds.is_active = True
        
        db.commit()
        print("✅ Setup complete for trader1 with cTrader!")
        print(f"User ID: {user.id}")
        if acc:
            print(f"Broker Account ID: {acc.id}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error during setup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    setup_trader1_ctrader()
