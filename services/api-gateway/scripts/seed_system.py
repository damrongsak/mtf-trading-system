import sys
import os

# Add parent dir to path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.system_config import SystemConfig

def seed_system_config():
    db = SessionLocal()
    try:
        print("Seeding System Config...")
        
        configs = {
            "supported_timeframes": ["M5", "M15", "H1", "H4", "D", "W", "M"]
        }
        
        for key, value in configs.items():
            existing = db.query(SystemConfig).filter(SystemConfig.key == key).first()
            if not existing:
                config = SystemConfig(
                    key=key,
                    value=value,
                    description=f"Default {key.replace('_', ' ')}"
                )
                db.add(config)
                print(f"Added config: {key} = {value}")
            else:
                print(f"Config {key} already exists.")
        
        db.commit()
        print("System Config seeded successfully.")
        
    except Exception as e:
        print(f"Error seeding system config: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_system_config()
