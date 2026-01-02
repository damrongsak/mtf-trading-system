import requests
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

def verify_flow():
    # 1. Register User
    email = "test_plugin_user@example.com"
    password = "SecurePassword123!"
    
    # Register
    logger.info("Registering user...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "username": email,
        "password": password,
        "full_name": "Plugin Tester"
    })
    
    if resp.status_code == 400 and "already exists" in resp.text:
        logger.info("User already exists, proceeding to login.")
    elif resp.status_code != 200:
        logger.error(f"Registration failed: {resp.text}")
        sys.exit(1)

    # 2. Login
    logger.info("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/token", data={
        "username": email,
        "password": password
    })
    
    if resp.status_code != 200:
        logger.error(f"Login failed: {resp.text}")
        sys.exit(1)
        
    token = resp.json()["auth"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    logger.info("✅ Login successful, token obtained.")

    # 3. List Plugins (Expect 1)
    logger.info("Listing plugins...")
    resp = requests.get(f"{BASE_URL}/plugins", headers=headers)
    if resp.status_code != 200:
        logger.error(f"List plugins failed: {resp.text}")
        sys.exit(1)
    
    plugins = resp.json()
    logger.info(f"Found plugins: {len(plugins)}")
    target_plugin = next((p for p in plugins if p["id"] == "olympus-lstm-predictor"), None)
    
    if not target_plugin:
        logger.error("❌ Olympus LSTM Predictor not found in list!")
        sys.exit(1)
        
    logger.info(f"✅ Found target plugin: {target_plugin['name']}")

    # 4. Activate Plugin
    logger.info("Activating plugin...")
    resp = requests.post(f"{BASE_URL}/plugins/olympus-lstm-predictor/activate", headers=headers)
    
    if resp.status_code != 200:
        logger.error(f"Activation failed: {resp.text}")
        sys.exit(1)
        
    logger.info("✅ Plugin activated successfully via API.")
    
    # 5. Verify Activation Status
    resp = requests.get(f"{BASE_URL}/plugins", headers=headers)
    active_plugin = next((p for p in resp.json() if p["id"] == "olympus-lstm-predictor"), None)
    
    if active_plugin and active_plugin.get("is_active"):
        logger.info("✅ Plugin confirmed ACTIVE in API response.")
    else:
        logger.error("❌ Plugin state not updated to ACTIVE.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        verify_flow()
    except Exception as e:
        logger.error(f"Verification script crashed: {e}")
        sys.exit(1)
