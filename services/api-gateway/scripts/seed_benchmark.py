import sys
import os
from datetime import datetime, timedelta
import random
import uuid

# Add parent directory to path so we can import 'app'
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from app.database import SessionLocal, engine
from app.models import MarketSymbol, Candle, MarketCategory
from app.models.data_source import DataSource
from sqlalchemy import text

def seed_benchmark():
    db = SessionLocal()
    try:
        # 1. Ensure 'Metals' Category exists
        category_name = "Metals"
        category = db.query(MarketCategory).filter(MarketCategory.name == category_name).first()
        if not category:
             category = MarketCategory(id=uuid.uuid4(), name=category_name, is_active=True)
             db.add(category)
             db.commit()
             db.refresh(category)
             
        # 2. Ensure 'OANDA' DataSource exists
        ds_name = "OANDA"
        ds = db.query(DataSource).filter(DataSource.name == ds_name).first()
        if not ds:
             ds = DataSource(
                 id=uuid.uuid4(), 
                 name=ds_name, 
                 type="api", 
                 config_json={}, 
                 is_active=True
             )
             db.add(ds)
             db.commit()
             db.refresh(ds)
        
        # 3. Ensure XAU/USD market symbol exists
        symbol_code = "XAU/USD"
        ms = db.query(MarketSymbol).filter(MarketSymbol.symbol == symbol_code).first()
        
        if not ms:
            print(f"Creating MarketSymbol: {symbol_code}")
            ms = MarketSymbol(
                id=str(uuid.uuid4()),
                symbol=symbol_code,
                display_name="Gold / US Dollar",
                category_id=category.id, # Link to category
                data_source_id=ds.id,    # Link to data source
            )
            db.add(ms)
            db.commit()
            db.refresh(ms)
        else:
            # Update existing to ensure it has data source if it didn't
            if not ms.data_source_id:
                 ms.data_source_id = ds.id
                 db.commit()
            print(f"Found MarketSymbol: {symbol_code}")

        # 3. Check if we have D1 candles
        count = db.query(Candle).filter(
            Candle.market_symbol_id == ms.id, 
            Candle.timeframe == 'D1'
        ).count()
        
        if count > 300:
            print(f"Benchmark data already seeded ({count} candles). Skipping.")
            return

        print("Seeding ~365 days of mock Benchmark data...")
        
        start_price = 2000.0
        current_date = datetime.utcnow() - timedelta(days=365)
        candles = []
        
        for _ in range(365):
            change = random.uniform(-0.01, 0.011) # Slight upward bias
            close_price = start_price * (1 + change)
            high_price = max(start_price, close_price) * (1 + random.uniform(0, 0.005))
            low_price = min(start_price, close_price) * (1 - random.uniform(0, 0.005))
            
            candles.append(Candle(
                id=str(uuid.uuid4()),
                market_symbol_id=ms.id,
                timeframe='D1',
                timestamp=current_date,
                open=start_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=random.randint(1000, 5000),
                is_complete=True
            ))
            
            start_price = close_price
            current_date += timedelta(days=1)
            
        db.bulk_save_objects(candles)
        db.commit()
        print("Benchmark data seeded successfully.")

    except Exception as e:
        print(f"Error seeding benchmark: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_benchmark()
