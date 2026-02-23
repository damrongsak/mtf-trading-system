import asyncio
import httpx
import json
import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("accuracy-audit")

API_URL = "http://api-gateway:8000"
USER_CREDENTIALS = {"username": "trader1", "password": "password123"}

async def get_auth_context():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/v1/auth/token", data=USER_CREDENTIALS)
        resp.raise_for_status()
        data = resp.json()
        return {
            "token": data["auth"]["access_token"],
            "user_id": data["data"]["id"]
        }

async def audit_risk_math(token: str):
    """
    Audit Test: Verify that the risk calculation logic is mathematically precise.
    Scenario: XAUUSD, Balance=$1000, Risk=1%, Entry=2000, SL=1990.
    Expected: Risk=$10, Units=1, Lots=0.01.
    """
    logger.info("🛡️ Auditing Risk Calculation Precision...")
    
    payload = {
        "symbol": "XAUUSD",
        "entry_price": 2000.0,
        "stop_loss": 1990.0,
        "take_profit": 2015.0,
        "account_balance": 1000.0,
        "risk_percentage": 1.0
    }
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/v1/risk/check", json=payload, headers=headers)
        resp.raise_for_status()
        # API Gateway returns success_response(data=strategy_core_json)
        # And strategy-core returns {"data": {...}}
        outer_data = resp.json()["data"]
        data = outer_data["data"]
        
        lots = data["position_size"]["lots"]
        units = data["position_size"]["units"]
        rr = data["risk_reward_ratio"]
        
        # Verification
        assert lots == 0.01, f"Lots mismatch: expected 0.01, got {lots}"
        assert units == 1.0, f"Units mismatch: expected 1.0, got {units}"
        assert rr == 1.5, f"R:R mismatch: expected 1.5, got {rr}"
        
        logger.info(f"✅ Risk Math Verified: Lots={lots}, Units={units}, R:R={rr}")

async def audit_smc_slim_consistency():
    """
    Audit Test: Verify that 'Slim Mode' correctly distills data without loss of critical signal.
    """
    logger.info("🔍 Auditing SMC Slim Mode Distiller Logic...")
    
    # Verification of the distiller logic itself
    from app.utils.distiller import DataDistiller
    
    # Mock raw SMC data
    mock_raw = {
        "direction": "LONG",
        "entry_price": 2000.0,
        "analysis": {
            "order_blocks": [
                {"index": 1, "type": "bullish", "top": 1990.0, "bottom": 1980.0},
                {"index": 2, "type": "bullish", "top": 1995.0, "bottom": 1992.0}
            ],
            "fvgs": [
                {"index": 1, "type": "bullish", "top": 1998.0, "bottom": 1997.0}
            ]
        }
    }
    
    slim = DataDistiller.distill_smc_raw(mock_raw)
    
    assert slim["direction"] == "LONG"
    assert len(slim["order_blocks"]) == 2
    # Check that sorting works (though index 2 is most recent in real case, here just testing presence)
    assert any(ob["top"] == 1995.0 for ob in slim["order_blocks"])
    
    logger.info("✅ Slim Mode Distiller Logic Verified.")

async def audit_trace_propagation(token: str, user_id: str):
    """
    Audit Test: Verify that a single Request-ID flows through the entire system.
    """
    logger.info("🧵 Auditing Trace Propagation Flow...")
    
    request_id = f"audit-trace-{int(asyncio.get_event_loop().time())}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": request_id
    }
    
    async with httpx.AsyncClient() as client:
        # Call a complex multi-service endpoint
        resp = await client.post(
            f"{API_URL}/api/v1/ai/chat/sessions/message",
            json={
                "message": "What is the current XAUUSD sentiment?",
                "user_id": user_id
            },
            headers=headers,
            timeout=120.0
        )
        resp.raise_for_status()
        
        # Verify response header
        returned_id = resp.headers.get("X-Request-ID")
        assert returned_id == request_id, f"Trace ID mismatch: expected {request_id}, got {returned_id}"
        
        logger.info(f"✅ Trace ID successfully propagated and returned: {returned_id}")

async def main():
    try:
        ctx = await get_auth_context()
        token = ctx["token"]
        user_id = ctx["user_id"]
        
        await audit_risk_math(token)
        await audit_smc_slim_consistency()
        await audit_trace_propagation(token, user_id)
        logger.info("\n🏆 ALL ACCURACY AUDITS PASSED 🏆")
    except Exception as e:
        import traceback
        logger.error(f"❌ Audit Failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    # Add app directory to path so we can import distiller
    import os
    sys.path.append(os.path.join(os.getcwd(), "services/ai-analyst"))
    asyncio.run(main())
