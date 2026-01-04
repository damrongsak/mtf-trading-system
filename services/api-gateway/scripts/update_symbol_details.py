import sys
import os
import httpx
import json

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.market import MarketSymbol
from app.models.data_source import DataSource

# OANDA Configuration
OANDA_API_URL = "https://api-fxtrade.oanda.com/v3"  # Default to Live
if os.getenv("OANDA_ENV", "practice") == "practice":
    OANDA_API_URL = "https://api-fxpractice.oanda.com/v3"

TOKEN = os.getenv("OANDA_API_TOKEN") or os.getenv("OANDA_API_KEY")
ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")

def get_oanda_instruments():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{OANDA_API_URL}/accounts/{ACCOUNT_ID}/instruments"
    print(f"Fetching instruments from: {url}")
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get("instruments", [])
    except httpx.RequestError as e:
        print(f"Error fetching from OANDA: {e}")
        return []
    except httpx.HTTPStatusError as e:
         print(f"Response: {e.response.text}")
         return []

def update_details():
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
            print("Error: OANDA DataSource not found in DB.")
            return
            
        print(f"Updating symbols for DataSource: {oanda_ds.name} (ID: {oanda_ds.id})")
        
        updated_count = 0
        skipped_count = 0
        
        for instrument in instruments:
            name = instrument['name'] # e.g. EUR_USD
            
            # Find symbol
            sym = db.query(MarketSymbol).filter(
                MarketSymbol.symbol == name, 
                MarketSymbol.data_source_id == oanda_ds.id
            ).first()
            
            if sym:
                # Check if update needed
                if sym.details != instrument:
                    sym.details = instrument
                    db.add(sym)
                    updated_count += 1
                else:
                    skipped_count += 1
            else:
                # If symbol doesn't exist, we skip it (use sync_oanda_symbols.py to create)
                # Or we could create it here, but let's focus on 'update details'
                pass
                    
        db.commit()
        print(f"Successfully processed. Updated {updated_count} symbols with new details. Skipped {skipped_count} unchanged.")

    except Exception as e:
        print(f"Error updating details: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    update_details()
