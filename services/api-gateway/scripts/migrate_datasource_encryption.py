import os
import sys
import logging
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.data_source import DataSource
from app.utils.crypto import encrypt_data, decrypt_data

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Migration")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://trader:trader@mtf-postgres:5432/mtf_db")

def migrate():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        sources = session.query(DataSource).all()
        logger.info(f"Found {len(sources)} Data Sources to check...")
        
        migrated_count = 0
        for source in sources:
            config = source.config_json
            
            # Check if already encrypted
            is_encrypted = False
            if isinstance(config, str):
                try:
                    decrypt_data(config)
                    is_encrypted = True
                except Exception:
                    # Might be a plain string if it's not a dict, but usually it's a dict or encrypted blob
                    pass
            
            if is_encrypted:
                logger.info(f"  - Source '{source.name}' is already encrypted. Skipping.")
                continue
            
            if isinstance(config, dict):
                logger.info(f"  - Encrypting source '{source.name}'...")
                source.config_json = encrypt_data(config)
                migrated_count += 1
            else:
                logger.warning(f"  - Source '{source.name}' has unexpected config type: {type(config)}. Skipping.")

        if migrated_count > 0:
            session.commit()
            logger.info(f"✅ Successfully migrated {migrated_count} Data Sources.")
        else:
            logger.info("No Data Sources needed migration.")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate()
