from app.database import SessionLocal
from app.models.api_key import ApiKey
from app.utils.crypto import encrypt_data
import uuid
import os

def seed_test_key():
    db = SessionLocal()
    user_id = "93cb8075-0e29-47f9-a939-8f413fb1dac4"
    test_key = "test_api_key_123"
    test_secret = "test_secret_456"

    # Check if already exists
    existing = db.query(ApiKey).filter(ApiKey.api_key == test_key).first()
    if existing:
        print(f"API Key {test_key} already exists.")
        return

    # Secret is stored as encrypt_data({"secret": test_secret})
    encrypted_secret = encrypt_data({"secret": test_secret})

    key_entry = ApiKey(
        user_id=uuid.UUID(user_id),
        name="Test Key",
        api_key=test_key,
        api_secret=encrypted_secret,
        is_active=True
    )
    db.add(key_entry)
    db.commit()
    print(f"Created API Key: {test_key} Secret: {test_secret}")

if __name__ == "__main__":
    seed_test_key()
