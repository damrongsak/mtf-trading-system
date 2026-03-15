import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

from app.database import DATABASE_URL
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

load_dotenv()

CORE_SYMBOLS = ["XAU_USD", "EUR_USD", "USD_JPY", "BTC_USD", "WTI_USD"]

def cleanup_symbols():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 1. Find CTRADER Data Source
        ds = db.query(DataSource).filter(DataSource.provider == 'CTRADER').first()
        if not ds:
            print("❌ CTrader Data Source not found.")
            return

        print(f"🔍 Analyzing symbols for Data Source: {ds.id} ({ds.name})")

        # 2. Identify all active symbols for this DS
        all_active = db.query(MarketSymbol).filter(
            MarketSymbol.data_source_id == ds.id,
            MarketSymbol.is_active == True
        ).all()

        print(f"📊 Currently active: {len(all_active)}")

        # 3. Deactivate those NOT in CORE
        # We also need to check mapping (e.g. XAUUSD vs XAU_USD)
        core_clean = [s.replace("_", "") for s in CORE_SYMBOLS]
        
        deactivated_count = 0
        for ms in all_active:
            # Check if this symbol matches a core symbol (raw or with underscore)
            ms_clean = ms.symbol.replace("_", "").replace("/", "")
            if ms_clean not in core_clean and ms.symbol not in CORE_SYMBOLS:
                ms.is_active = False
                deactivated_count += 1
            else:
                print(f"✨ Keeping core symbol: {ms.symbol}")

        db.commit()
        print(f"✅ Deactivated {deactivated_count} unnecessary symbols.")
        
        # 4. Refresh count
        remaining = db.query(MarketSymbol).filter(
            MarketSymbol.data_source_id == ds.id,
            MarketSymbol.is_active == True
        ).count()
        print(f"📈 Remaining active symbols for cTrader: {remaining}")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_symbols()
