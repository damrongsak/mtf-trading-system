
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
                    "host": os.getenv("CTRADER_HOST", "live.ctraderapi.com"),
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

        from app.utils.crypto import encrypt_data
        
        # 4. Ensure BrokerAccount Exists (Deduplicate by name or number)
        account = db.query(BrokerAccount).filter(
            (BrokerAccount.account_name == 'CTrader Demo') | 
            (BrokerAccount.account_number == account_id)
        ).first()
        creds = {
            "app_id": client_id,
            "secret": client_secret,
            "account_id": account_id,
            "token": token,
            "refresh_token": refresh_token
        }
        
        if not account:
            print("Creating cTrader BrokerAccount...")
            account = BrokerAccount(
                id=uuid.uuid4(),
                fund_id=fund.id,
                broker_name="CTRADER",
                account_name="CTrader Demo",
                credentials_encrypted=encrypt_data(creds),
                is_live=False,
                is_active=True,
                supported_symbols=["XAU/USD", "EUR/USD", "GBP/USD", "USD/JPY"]
            )
            db.add(account)
            db.commit()
        else:
             print("Updating cTrader BrokerAccount credentials (encrypted)...")
             account.credentials_encrypted = encrypt_data(creds)
             db.commit()

        # 5. Ensure All Core Symbols exist for cTrader
        # Categories mapping for new symbols
        symbol_categories = {
            "Forex": ["EUR_USD", "USD_JPY"],
            "Crypto": ["BTC_USD"],
            "Metals": ["XAU_USD"],
            "Commodities": ["WTI_USD"]
        }
        
        # cTrader Metadata mapping (Common defaults)
        symbol_metadata = {
            "XAU_USD": {"id": "1", "lot_size": 10000000, "digits": 2, "pipPosition": 1},
            "EUR_USD": {"id": "2", "lot_size": 100000, "digits": 5, "pipPosition": -4},
            "USD_JPY": {"id": "4", "lot_size": 100000, "digits": 3, "pipPosition": -2},
            "BTC_USD": {"id": "100", "lot_size": 100, "digits": 2, "pipPosition": 0.01}, 
            "WTI_USD": {"id": "50", "lot_size": 1000, "digits": 3, "pipPosition": -2, "broker_symbol": "XTIUSD"}
        }

        for cat_name, symbols in symbol_categories.items():
            cat = db.query(MarketCategory).filter(MarketCategory.name == cat_name).first()
            if not cat:
                cat = MarketCategory(name=cat_name)
                db.add(cat)
                db.commit()
                db.refresh(cat)

            for symbol_name in symbols:
                meta = symbol_metadata.get(symbol_name, {})
                
                # Standardized Details for cTrader
                ctrader_details = {
                    "symbol_id": meta.get("id"),
                    "lot_size": meta.get("lot_size"),
                    "digits": meta.get("digits"), 
                    "pipPosition": meta.get("pipPosition"),
                    "minLot": 0.01,
                    "maxLot": 100.0,
                    "step_volume": 0.01,
                    "symbolName": meta.get("broker_symbol") or symbol_name.replace("_", ""),
                    "raw": {"symbolId": meta.get("id"), "digits": meta.get("digits"), "lotSize": meta.get("lot_size")}
                }

                symbol = db.query(MarketSymbol).filter(
                    MarketSymbol.symbol == symbol_name,
                    MarketSymbol.data_source_id == ds.id
                ).first()

                if not symbol:
                    print(f"Creating Symbol {symbol_name} for cTrader...")
                    symbol = MarketSymbol(
                        id=uuid.uuid4(),
                        category_id=cat.id,
                        data_source_id=ds.id,
                        symbol=symbol_name,
                        display_name=symbol_name.replace("_", "/"),
                        details=ctrader_details,
                        is_active=True
                    )
                    db.add(symbol)
                else:
                    print(f"Updating details for {symbol_name} (cTrader)...")
                    # Merge/Update details
                    current_details = symbol.details or {}
                    current_details.update(ctrader_details)
                    symbol.details = current_details
                
                db.commit()
        
        print("✅ cTrader Master Data Initialization Complete.")

    except Exception as e:
        print(f"❌ Error seeding cTrader data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_ctrader()
