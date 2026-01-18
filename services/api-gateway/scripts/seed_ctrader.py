
import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load env
load_dotenv()

from app.database import DATABASE_URL
from app.models.data_source import DataSource
from app.models.broker_account import BrokerAccount
from app.models.user_fund import Fund
from app.models.market import MarketSymbol, MarketCategory

def seed_ctrader():
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set.")
        return

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("🚀 Seeding cTrader Master Data...")

        # 1. Credentials from Env
        client_id = os.getenv("CTRADER_CLIENT_ID")
        client_secret = os.getenv("CTRADER_CLIENT_SECRET")
        account_id = os.getenv("CTRADER_ACCOUNT_ID")
        token = os.getenv("CTRADER_TOKEN")
        refresh_token = os.getenv("CTRADER_REFRESH_TOKEN")
        
        if not all([client_id, client_secret, account_id, token]):
            print("⚠️ Missing cTrader credentials in env. Using placeholders.")
            client_id = client_id or "INSERT_APP_ID"
            client_secret = client_secret or "INSERT_SECRET"
            account_id = account_id or "INSERT_ACC_ID"
            token = token or "INSERT_TOKEN"
            refresh_token = refresh_token or "INSERT_REFRESH_TOKEN"

        # 2. Ensure Fund Exists
        fund = db.query(Fund).first()
        if not fund:
            print("Creating Default Fund...")
            fund = Fund(
                name="Olympus Fund",
                description="Default Fund",
                strategy_type="MTF_SMC_BASIC",
                max_risk_per_trade=100.0,
                risk_percentage=0.01
            )
            db.add(fund)
            db.commit()
            db.refresh(fund)
        else:
             print(f"Using Fund: {fund.name} ({fund.id})")

        # 3. Ensure DataSource Exists
        ds = db.query(DataSource).filter(DataSource.provider == 'CTRADER').first()
        if not ds:
            print("Creating cTrader DataSource...")
            ds = DataSource(
                id=uuid.uuid4(),
                provider="CTRADER",
                name="CTrader Data",
                type="websocket",
                config_json={
                    "host": "demo.ctraderapi.com",
                    "port": 5035,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "account_id": account_id,
                    "token": token
                },
                is_active=True
            )
            db.add(ds)
            db.commit()
            db.refresh(ds)
        else:
            print("cTrader DataSource already exists.")

        # 4. Ensure BrokerAccount Exists
        account = db.query(BrokerAccount).filter(BrokerAccount.broker_name == 'CTRADER').first()
        if not account:
            print("Creating cTrader BrokerAccount...")
            account = BrokerAccount(
                id=uuid.uuid4(),
                fund_id=fund.id,
                broker_name="CTRADER",
                account_name="CTrader Demo",
                credentials_encrypted={
                    "app_id": client_id,
                    "secret": client_secret,
                    "account_id": account_id,
                    "token": token,
                    "refresh_token": refresh_token
                },
                is_live=False,
                is_active=True,
                supported_symbols=["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY"]
            )
            db.add(account)
            db.commit()
        else:
             print("cTrader BrokerAccount already exists.")

        # 5. Ensure MarketSymbol exists and is linked
        # Ensure 'Metals' Category
        cat = db.query(MarketCategory).filter(MarketCategory.name == "Metals").first()
        if not cat:
            cat = MarketCategory(name="Metals")
            db.add(cat)
            db.commit()
            
        symbol_name = "XAU/USD"
        symbol = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol_name).first()
        if not symbol:
            print(f"Creating Symbol {symbol_name}...")
            symbol = MarketSymbol(
                id=uuid.uuid4(),
                category_id=cat.id,
                data_source_id=ds.id, # Link to CTrader as default source?
                symbol=symbol_name,
                display_name="Gold vs USD",
                details={
                    "digits": 2, 
                    "pipPosition": 1,
                    "ctrader_symbol_id":  "1" # Just generic XAUUSD ID, requires lookup really
                }
            )
            db.add(symbol)
            db.commit()
        else:
            # Update data source if not set?
            if not symbol.data_source_id:
                print(f"Linking {symbol_name} to cTrader DataSource...")
                symbol.data_source_id = ds.id
                db.commit()
        
        print("✅ cTrader Master Data Initialization Complete.")

    except Exception as e:
        print(f"❌ Error seeding cTrader data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_ctrader()
