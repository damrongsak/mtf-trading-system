
import requests
import json
import logging
from datetime import datetime, timedelta
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

def check_endpoint(method, url, payload=None, params=None, expected_status=200, description=""):
    full_url = f"{BASE_URL}{url}"
    logger.info(f"Checking {description} [{method} {full_url}]...")
    try:
        if method == "GET":
            response = requests.get(full_url, params=params)
        elif method == "POST":
            response = requests.post(full_url, json=payload)
        elif method == "PATCH":
            response = requests.patch(full_url, json=payload)
        else:
            logger.error(f"Unsupported method {method}")
            return False

        if response.status_code == expected_status:
            logger.info(f"✅ PASS: {description}")
            return True
        else:
            logger.error(f"❌ FAIL: {description} - Status: {response.status_code}, Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ FAIL: {description} - Exception: {e}")
        return False

def main():
    logger.info("Starting Service Verification...")
    
    # 1. Check Health (via Root or Docs)
    # Fastapi usually has /docs working if root isn't defined
    try:
        r = requests.get("http://localhost:8000/docs")
        if r.status_code == 200:
            logger.info("✅ PASS: Service is reachable (Docs)")
        else:
            logger.error("❌ FAIL: Service unreachable")
            sys.exit(1)
    except:
        logger.error("❌ FAIL: Service unreachable")
        sys.exit(1)

    # 2. Market Symbols
    success = check_endpoint("GET", "/symbols", params={"broker": "OANDA"}, expected_status=200, description="Get Active Symbols")
    
    # 3. Candles (Pagination)
    # Ensure at least one symbol exists or check empty list is 200
    success &= check_endpoint("GET", "/candles", params={"symbol": "EUR_USD", "timeframe": "M15", "limit": 10}, expected_status=200, description="Get Candles")

    # 4. Trigger Backfill
    # Use a safe backfill (short range)
    backfill_payload = {
        "symbol": "EUR_USD",
        "timeframe": "M15",
        "from_date": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        "to_date": datetime.utcnow().isoformat()
    }
    success &= check_endpoint("POST", "/backfill", payload=backfill_payload, expected_status=202, description="Trigger Backfill Job")

    # 5. Manual Ingest Trigger
    success &= check_endpoint("POST", "/ingest/manual", params={"symbol": "EUR_USD"}, expected_status=202, description="Trigger Manual Ingestion")

    # 6. Stream Refresh
    success &= check_endpoint("POST", "/stream/refresh", expected_status=200, description="Refresh Streams")

    if success:
        logger.info("\n🎉 All Verification Checks Passed!")
        sys.exit(0)
    else:
        logger.error("\n⚠️ Some Verification Checks Failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
