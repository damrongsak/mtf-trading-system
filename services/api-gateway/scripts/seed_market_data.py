import sys
import os
# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.market import MarketCategory, MarketSymbol
from app.models.data_source import DataSource
import json

def seed_data():
    db = SessionLocal()
    try:
        print("Seeding Market Categories...")
        
        # Categories
        categories = {
            "Forex": ["EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CAD"],
            "Crypto": ["BTC_USD", "ETH_USD", "SOL_USD"],
            "Metals": ["XAU_USD", "XAG_USD"]
        }
        
        for idx, (cat_name, symbols) in enumerate(categories.items()):
            cat = db.query(MarketCategory).filter(MarketCategory.name == cat_name).first()
            if not cat:
                cat = MarketCategory(name=cat_name, order_index=idx)
                db.add(cat)
                db.commit()
                db.refresh(cat)
                print(f"Created category: {cat_name}")
            
            for s_idx, symbol in enumerate(symbols):
                sym = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol, MarketSymbol.category_id == cat.id).first()
                if not sym:
                    sym = MarketSymbol(
                        category_id=cat.id, 
                        symbol=symbol, 
                        display_name=symbol.replace("_", "/"),
                        order_index=s_idx
                    )
                    db.add(sym)
                    print(f"  Added symbol: {symbol}")
        
        db.commit()
        print("Market Data seeded successfully.")
        
        print("Seeding OANDA DataSource...")
        ds = db.query(DataSource).filter(DataSource.name == "OANDA").first()
        if not ds:
            # Create a placeholder or real config if available
            # Warning: Using placeholder token. User must update.
            config = {
                "token": os.getenv("OANDA_API_TOKEN", "REPLACE_ME"),
                "account_id": os.getenv("OANDA_ACCOUNT_ID", "REPLACE_ME"),
                "environment": "practice"
            }
            ds = DataSource(
                name="OANDA",
                type="api",
                config_json=config,
                is_active=True
            )
            db.add(ds)
            db.commit()
            print("Created OANDA DataSource (Requires valid credentials).")
        else:
            print("OANDA DataSource already exists.")

    except Exception as e:
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
