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
        print("Seeding OANDA DataSource...")
        ds = db.query(DataSource).filter(DataSource.name == "OANDA").first()
        if not ds:
            config = {
                "api_key": os.getenv("OANDA_API_KEY", "REPLACE_ME"),
                "account_id": os.getenv("OANDA_ACCOUNT_ID", "REPLACE_ME"),
                "environment": os.getenv("OANDA_ENV", "live")
            }
            ds = DataSource(
                name="OANDA",
                provider="OANDA",
                type="api",
                config_json=config,
                is_active=True
            )
            db.add(ds)
            db.commit()
            db.refresh(ds)
            print("Created OANDA DataSource.")
        else:
            print("OANDA DataSource already exists.")

        print("Seeding Market Categories and Symbols...")
        
        # Categories
        categories = {
            "Forex": ["EUR_USD", "USD_JPY"],
            "Crypto": ["BTC_USD"],
            "Metals": ["XAU_USD"],
            "Commodities": ["WTI_USD"]
        }
        
        # Broker-specific mappings for OANDA
        broker_mapping = {
            "WTI_USD": "WTICO_USD",
            "XAU_USD": "XAU_USD",
            "EUR_USD": "EUR_USD",
            "USD_JPY": "USD_JPY",
            "BTC_USD": "BTC_USD"
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
                # Check for symbol + data_source_id uniqueness
                sym = db.query(MarketSymbol).filter(
                    MarketSymbol.symbol == symbol, 
                    MarketSymbol.data_source_id == ds.id
                ).first()
                
                # Standardized details for OANDA mapping
                oanda_details = {
                    "symbolName": broker_mapping.get(symbol, symbol.replace("_", "/")),
                    "broker_symbol": broker_mapping.get(symbol)
                }
                
                if not sym:
                    sym = MarketSymbol(
                        category_id=cat.id, 
                        symbol=symbol, 
                        display_name=symbol.replace("_", "/"),
                        order_index=s_idx,
                        data_source_id=ds.id,
                        details=oanda_details,
                        is_active=True
                    )
                    db.add(sym)
                    print(f"  Added symbol: {symbol} (OANDA: {oanda_details['symbolName']})")
                else:
                    print(f"  Updating details for {symbol} (OANDA)...")
                    sym.details = oanda_details
        
        db.commit()
        print("Market Data seeded successfully.")

    except Exception as e:
        print(f"Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
