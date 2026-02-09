"""
Simple utility for encrypting/decrypting sensitive data like Telegram bot tokens.
Uses the existing SETTINGS_ENCRYPTION_KEY from .env
"""
from cryptography.fernet import Fernet
import os
import base64


def get_cipher():
    """Get Fernet cipher using the encryption key from environment"""
    key = os.getenv("SETTINGS_ENCRYPTION_KEY")
    if not key:
        raise ValueError("SETTINGS_ENCRYPTION_KEY not found in environment")
    
    # Ensure the key is properly formatted for Fernet
    try:
        return Fernet(key.encode())
    except Exception as e:
        raise ValueError(f"Invalid encryption key format: {e}")


def encrypt_token(token: str) -> str:
    """Encrypt a token (e.g., Telegram bot token)"""
    if not token:
        return ""
    
    cipher = get_cipher()
    encrypted = cipher.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token"""
    if not encrypted_token:
        return ""
    
    cipher = get_cipher()
    decrypted = cipher.decrypt(encrypted_token.encode())
    return decrypted.decode()
