import pytest
import os
from app.utils.crypto import encrypt_data, decrypt_data, get_cipher

def test_encryption_decryption():
    # Set encryption key for test
    os.environ["SETTINGS_ENCRYPTION_KEY"] = "b8P2nnUaxDqYEcFIEMM-7ROBMAfqw2ksw8YVSRRK7_o="
    get_cipher.cache_clear() # Ensure clean state
    
    test_data = {
        "api_key": "secret-123",
        "account_id": "acc-456",
        "is_live": False
    }
    
    # Encrypt
    encrypted = encrypt_data(test_data)
    assert isinstance(encrypted, str)
    assert len(encrypted) > 0
    assert encrypted != str(test_data)
    
    # Decrypt
    decrypted = decrypt_data(encrypted)
    assert decrypted == test_data
    assert decrypted["api_key"] == "secret-123"

def test_encryption_fails_without_key():
    # Unset key
    old_key = os.environ.get("SETTINGS_ENCRYPTION_KEY")
    old_testing = os.environ.get("TESTING")
    
    if "SETTINGS_ENCRYPTION_KEY" in os.environ:
        del os.environ["SETTINGS_ENCRYPTION_KEY"]
    
    # Force TESTING=False to verify production behavior
    os.environ["TESTING"] = "False"
    get_cipher.cache_clear()
    
    try:
        with pytest.raises(ValueError, match="SETTINGS_ENCRYPTION_KEY environment variable is not set"):
            encrypt_data({"test": "data"})
    finally:
        # Restore key if it was there
        if old_key:
            os.environ["SETTINGS_ENCRYPTION_KEY"] = old_key
        if old_testing:
            os.environ["TESTING"] = old_testing
        else:
            if "TESTING" in os.environ:
                del os.environ["TESTING"]
        get_cipher.cache_clear()
