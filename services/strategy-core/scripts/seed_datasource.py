
import sys
import os
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Load explicitly from .env file
load_dotenv()

from app.models.data_source import DataSource
from app.database import Base, DATABASE_URL

def seed_datasource():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Check if OANDA datasource exists (case insensitive check done in app, here we use exact name)
        existing = db.query(DataSource).filter(DataSource.name == 'OANDA').first()
        if existing:
            print("DataSource 'OANDA' already exists.")
            return

        print("Seeding 'OANDA' DataSource...")
        
        # Get credentials from env or use placeholders
        token = os.getenv("OANDA_API_KEY", "REPLACE_WITH_TOKEN")
        account_id = os.getenv("OANDA_ACCOUNT_ID", "REPLACE_WITH_ACCOUNT_ID")
        
        oanda_source = DataSource(
            id=uuid.uuid4(),
            name="OANDA",
            provider="OANDA",
            type="api",
            config_json={
                "token": token,
                "account_id": account_id,
                "hostname": "api-fxpractice.oanda.com",
                "streaming_hostname": "stream-fxpractice.oanda.com"
            },
            schema_json={},
            is_active=True
        )
        
        db.add(oanda_source)
        db.commit()
        print("✅ Successfully seeded 'OANDA' DataSource.")
        
    except Exception as e:
        print(f"❌ Error seeding datasource: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_datasource()
