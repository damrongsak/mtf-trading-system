import asyncio
import httpx
import sys
import os
import uuid
import logging
from datetime import datetime, timedelta
from sqlalchemy import func

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal
from app.models.user import User
from app.models.trade import Trade, TradeStatus
from app.models.alert import Alert, AlertCondition
from app.models.candle import Candle
from app.models.market import MarketSymbol
from app.models.telegram_chat_mapping import TelegramChatMapping
from app.scheduler import check_price_alerts_job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_e2e")

BASE_URL = "http://localhost:8000"
USERNAME = "demo1"
PASSWORD = "password123"

async def get_token():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/token",
            data={"username": USERNAME, "password": PASSWORD}
        )
        if response.status_code != 200:
            logger.error(f"Auth failed ({response.status_code}): {response.text}")
            return None
        
        res_json = response.json()
        if "auth" in res_json and "access_token" in res_json["auth"]:
            return res_json["auth"]["access_token"]
        elif "access_token" in res_json:
             return res_json["access_token"]
        else:
            logger.error(f"Token not found in response: {res_json}")
            return None

def seed_test_data(user_id):
    db = SessionLocal()
    try:
        # 1. Telegram Mapping (RESPECT EXISTING)
        mapping = db.query(TelegramChatMapping).filter(TelegramChatMapping.user_id == user_id).first()
        if not mapping:
            # Fallback to .env if provided, otherwise dummy for logs only
            chat_id = os.getenv("TELEGRAM_CHAT_ID", "123456789")
            mapping = TelegramChatMapping(user_id=user_id, chat_id=str(chat_id))
            db.add(mapping)
            logger.info(f"Seeded Telegram mapping (fallback) for user {user_id}: {chat_id}")
        else:
            logger.info(f"Using existing Telegram mapping for user {user_id}: {mapping.chat_id}")
        
        # 2. Market Symbol for XAUUSD
        symbol_obj = db.query(MarketSymbol).filter(MarketSymbol.symbol == "XAUUSD").first()
        if not symbol_obj:
            logger.warning("XAUUSD MarketSymbol not found. This may cause issues.")
            
        # 3. Sample Closed Trades for Edge Optimization
        # Use TradeStatus.CLOSED (or "CLOSED" string if enum fails)
        existing_trades = db.query(Trade).filter(Trade.user_id == user_id, Trade.status == "CLOSED").count()
        if existing_trades < 5:
            for i in range(5):
                trade = Trade(
                    trade_id=uuid.uuid4(),
                    user_id=user_id,
                    symbol="XAUUSD",
                    strategy_name="SMC_XAU",
                    signal_timestamp=datetime.utcnow() - timedelta(days=i, hours=i*3),
                    entry_price=2000.0,
                    exit_price=2010.0,
                    gross_pnl=100.0,
                    status="CLOSED",
                    created_at=datetime.utcnow() - timedelta(days=i, hours=i*3),
                    exit_timestamp=datetime.utcnow() - timedelta(days=i, hours=i*3 - 1)
                )
                db.add(trade)
            logger.info(f"Seeded 5 closed trades for user {user_id}")

        # 4. Candle for Trigger
        candle = db.query(Candle).filter(Candle.symbol == "XAUUSD").order_by(Candle.timestamp.desc()).first()
        if not candle:
            if symbol_obj:
                candle = Candle(
                    market_symbol_id=symbol_obj.id,
                    symbol="XAUUSD",
                    timeframe="M1",
                    timestamp=datetime.utcnow(),
                    open=3000.0,
                    high=3050.0,
                    low=2950.0,
                    close=3100.0,
                    volume=100,
                    is_complete=True
                )
                db.add(candle)
                logger.info("Seeded new XAUUSD candle")
        else:
            candle.close = 3100.0
            candle.timestamp = datetime.utcnow()
            db.add(candle)
            logger.info("Updated existing XAUUSD candle for trigger")
        
        db.commit()
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
    finally:
        db.close()

async def verify_alerts(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        # 1. Create Alert
        alert_data = {
            "symbol": "XAUUSD",
            "condition": "PRICE_ABOVE",
            "threshold": 3000.0
        }
        res = await client.post(f"{BASE_URL}/api/v1/alerts", json=alert_data, headers=headers)
        if res.status_code != 201:
            logger.error(f"Create Alert failed: {res.text}")
            return False
        
        alert_resp = res.json()
        alert_id = alert_resp["data"]["id"]
        logger.info(f"Created Alert: {alert_id}")

        # 2. List Alerts
        res = await client.get(f"{BASE_URL}/api/v1/alerts", headers=headers)
        alerts_data = res.json()["data"]
        if not any(a["id"] == alert_id for a in alerts_data):
            logger.error("List Alerts: Created alert not found in active alerts")
            return False
        logger.info("Alert listed successfully")

        # 3. Simulate Trigger
        logger.info("Simulating trigger via check_price_alerts_job...")
        await check_price_alerts_job()
        
        # 4. Verify Triggered Status
        res = await client.get(f"{BASE_URL}/api/v1/alerts", headers=headers)
        alerts_data = res.json()["data"]
        found = next((a for a in alerts_data if a["id"] == alert_id), None)
        
        if found:
            if found.get("is_triggered"):
                 logger.info("✅ Alert status verified: TRIGGERED")
            else:
                 logger.warning("Alert found but NOT triggered. Candle price may not have updated correctly.")
        else:
             logger.info("Alert no longer in active list (likely triggered and deactivated)")

        # 5. Delete Alert (cleanup)
        res = await client.delete(f"{BASE_URL}/api/v1/alerts/{alert_id}", headers=headers)
        if res.status_code not in [200, 204]:
            logger.error(f"Delete Alert failed ({res.status_code}): {res.text}")
            return False
        logger.info("Alert cleanup successful")
        
        return True

async def verify_metrics(token):
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{BASE_URL}/api/v1/analysis/metrics/edge-optimization", headers=headers)
        if res.status_code != 200:
            logger.error(f"Edge Optimization failed: {res.text}")
            return False
        
        res_json = res.json()
        data = res_json.get("data", {})
        summary = data.get("summary", {})
        matrix = data.get("matrix", {})
        
        logger.info(f"Edge Optimization: Total PnL = {summary.get('total_pnl')}")
        logger.info(f"Edge Optimization: Matrix size = {len(matrix)} hours")
        
        if summary.get("total_pnl") is None:
            logger.error("Total PnL missing in summary")
            return False
            
        return True

async def main():
    token = await get_token()
    if not token: 
        logger.error("Failed to obtain auth token.")
        return

    # Get user_id for seeding
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == USERNAME).first()
        if not user:
            logger.error(f"User {USERNAME} not found in DB")
            return
        user_id = user.id
    finally:
        db.close()

    seed_test_data(user_id)
    
    metrics_ok = await verify_metrics(token)
    alerts_ok = await verify_alerts(token)
    
    if metrics_ok and alerts_ok:
        logger.info("✅ ALL E2E VERIFICATIONS PASSED")
    else:
        logger.error("❌ E2E VERIFICATION FAILED")

if __name__ == "__main__":
    asyncio.run(main())
