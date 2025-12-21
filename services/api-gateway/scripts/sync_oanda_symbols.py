import sys
import os
import requests
import re

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.market import MarketCategory, MarketSymbol
from app.models.data_source import DataSource

# OANDA Configuration
OANDA_API_URL = "https://api-fxtrade.oanda.com/v3"  # Default to Live
if os.getenv("OANDA_ENV", "practice") == "practice":
    OANDA_API_URL = "https://api-fxpractice.oanda.com/v3"

TOKEN = os.getenv("OANDA_API_TOKEN")
ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

def get_oanda_instruments():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{OANDA_API_URL}/accounts/{ACCOUNT_ID}/instruments"
    print(f"Fetching instruments from: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json().get("instruments", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching from OANDA: {e}")
        if hasattr(e, 'response') and e.response:
             print(f"Response: {e.response.text}")
        return []

def categorize_instrument(instrument):
    """
    Categorize instrument based on asset class/tags.
    OANDA returns tags like 'CURRENCY', 'CFD', 'METAL'.
    """
    # Check tags first if available (fetched instrument structure varies, checking common fields)
    tags = instrument.get("tags", [])
    
    # Fallback logic based on name
    name = instrument.get("name", "")
    type = instrument.get("type", "")
    
    if type == "CURRENCY":
        return "Forex"
    elif type == "CFD":
        if "XAU" in name or "XAG" in name:
            return "Metals"
        if "BTC" in name or "ETH" in name or "LTC" in name:
            return "Crypto"
        if "US30" in name or "SPX" in name or "NAS" in name or "DE30" in name:
            return "Indices"
        return "CFD" # Generic CFD
    elif type == "METAL":
        return "Metals"
        
    return "Other"

def sync_symbols():
    if not TOKEN or not ACCOUNT_ID:
        print("Error: OANDA_API_TOKEN and OANDA_ACCOUNT_ID environment variables must be set.")
        return

    db = SessionLocal()
    try:
        instruments = get_oanda_instruments()
        print(f"Fetched {len(instruments)} instruments from OANDA.")
        
        if not instruments:
            print("No instruments found or failed to fetch.")
            return

        # Fetch OANDA Data Source
        oanda_ds = db.query(DataSource).filter(DataSource.name == "OANDA").first()
        if not oanda_ds:
            print("Error: OANDA DataSource not found in DB. Please run seed_market_data.py first.")
            return
            
        print(f"Linking symbols to DataSource: {oanda_ds.name} (ID: {oanda_ds.id})")

        # Pre-create known categories order
        category_order = ["Forex", "Metals", "Crypto", "Indices", "CFD", "Other"]
        categories = {} # name -> db_obj
        
        for idx, cat_name in enumerate(category_order):
            cat = db.query(MarketCategory).filter(MarketCategory.name == cat_name).first()
            if not cat:
                cat = MarketCategory(name=cat_name, order_index=idx)
                db.add(cat)
                db.commit()
                db.refresh(cat)
                print(f"Created category: {cat_name}")
            categories[cat_name] = cat
            
        print("Syncing symbols...")
        count = 0
        updated_count = 0
        
        for instrument in instruments:
            name = instrument['name'] # e.g. EUR_USD
            display_name = instrument['displayName'] # e.g. EUR/USD
            
            cat_name = categorize_instrument(instrument)
            category = categories.get(cat_name, categories["Other"])
            
            # Upsert symbol
            sym = db.query(MarketSymbol).filter(MarketSymbol.symbol == name, MarketSymbol.category_id == category.id).first()
            if not sym:
                sym = MarketSymbol(
                    category_id=category.id,
                    symbol=name,
                    display_name=display_name,
                    data_source_id=oanda_ds.id,
                    order_index=999
                )
                db.add(sym)
                count += 1
            else:
                # Update display name or data source if missing
                changed = False
                if sym.display_name != display_name:
                    sym.display_name = display_name
                    changed = True
                if sym.data_source_id != oanda_ds.id:
                    sym.data_source_id = oanda_ds.id
                    changed = True
                
                if changed:
                     db.add(sym)
                     updated_count += 1
                    
        db.commit()
        print(f"Successfully synced. Added {count} new symbols, Updated {updated_count} existing symbols.")

    except Exception as e:
        print(f"Error syncing data: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    sync_symbols()
