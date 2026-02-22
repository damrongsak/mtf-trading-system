import asyncio
import httpx
import json
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_GATEWAY_URL = "http://api-gateway:8000"
USERNAME = "trader1"
PASSWORD = "password123"

# Simulated User Queries regarding OI and Strategy
QUERIES = [
    "What are the most significant short-term liquidity zones for XAUUSD right now? Are we near Max Pain?",
    "Give me a breakdown of the long-term institutional anchors for Gold. Should I be looking for macro reversals?",
    "Can you analyze XAUUSD open interest and tell me where the major supply and demand zones are located?",
    "I'm scalping Gold today. Based on the 0-7 DTE gamma levels, where are the key support and resistance walls?",
    "Synthesize an SMC technical analysis with the current Open Interest medium-term structure for XAUUSD."
]

async def authenticate() -> str:
    """Authenticates with the API Gateway and returns a JWT token."""
    logger.info(f"Authenticating as {USERNAME}...")
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_GATEWAY_URL}/api/v1/auth/token",
            data={"username": USERNAME, "password": PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token = response.json().get("auth", {}).get("access_token")
            # We also need the user_id for the chat payload. Usually part of the token or profile. 
            # We'll fetch the profile to get the UUID.
            logger.info("Authentication successful. Fetching user profile...")
            profile_resp = await client.get(
                f"{API_GATEWAY_URL}/api/v1/auth/profile",
                headers={"Authorization": f"Bearer {token}"}
            )
            user_id = profile_resp.json().get("data", {}).get("id")
            return token, user_id
        else:
            logger.error(f"Authentication failed: {response.text}")
            raise Exception("Failed to authenticate.")

async def send_query(token: str, user_id: str, query: str):
    """Sends a query to the AI Analyst agent endpoint."""
    logger.info(f"\n{'='*50}\n🤔 User Asks: '{query}'\n{'='*50}")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": query,
        "user_id": user_id
    }

    async with httpx.AsyncClient(timeout=180.0) as client:
        try:
            logger.info("🤖 AI Analyst is thinking... (This may take 10-30 seconds)")
            response = await client.post(
                f"{API_GATEWAY_URL}/api/v1/ai/chat/sessions/message",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # The endpoint returns a ChatMessage mapped to "response" or "content"
                reply = "No reply found."
                if "data" in data and isinstance(data["data"], dict):
                    reply = data["data"].get("response", data["data"].get("content", reply))
                elif "response" in data:
                    reply = data.get("response")
                elif "content" in data:
                    reply = data.get("content")
                    
                logger.info(f"\n💡 AI Analyst Reply:\n{reply}\n")
            else:
                logger.error(f"Failed to get response. Status Code: {response.status_code}\n{response.text}")
                
        except Exception as e:
            logger.error(f"Error querying {query}: {e}")
            
        logger.info("Waiting 15 seconds before next query to avoid rate limits...")
        await asyncio.sleep(15)

async def main():
    try:
        token, user_id = await authenticate()
        
        for q in QUERIES:
            await send_query(token, user_id, q)
            # Add a small delay between questions
            # The delay is now handled within send_query to ensure it happens after each query attempt
            
    except Exception as e:
        logger.error(f"Script execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
