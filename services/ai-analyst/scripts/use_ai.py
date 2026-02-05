import asyncio
import sys
import argparse
import json
import os
from pathlib import Path
from redis import asyncio as aioredis # type: ignore

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.gemini import GeminiClient
from app.core.config import settings

async def fetch_market_data(symbol: str = "XAU_USD"):
    """Fetches the latest market data for a symbol from Redis PubSub."""
    redis_url = settings.REDIS_URL
    # Normalize symbol for channel name (e.g., XAU_USD -> XAUUSD)
    normalized_symbol = symbol.replace("_", "").replace("/", "")
    channel_name = f"market_data:tick:{normalized_symbol}"
    
    try:
        redis = await aioredis.from_url(redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel_name)
        
        print(f"Listening for market data on channel: {channel_name}...")
        
        # Wait for a message with a short timeout
        message = None
        try:
            # First message is often subscribe confirmation, so we might need the next one
            # But get_message with ignore_subscribe_messages=True handles that
            
            # Simple loop with timeout
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < 2.0:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg['type'] == 'message':
                    message = msg['data']
                    break
                await asyncio.sleep(0.1)
                
        except Exception as e:
            print(f"Error reading from pubsub: {e}")
        
        await pubsub.unsubscribe(channel_name)
        await redis.aclose()
        
        if message:
            try:
                # Attempt to parse json
                return json.loads(message)
            except:
                return message
        return None
    except Exception as e:
        print(f"Warning: Could not fetch market data from Redis: {e}")
        return None

async def process_prompt(client: GeminiClient, prompt: str):
    # Fetch context
    market_data = await fetch_market_data("XAU_USD")
    
    enhanced_prompt = prompt
    if market_data:
        enhanced_prompt = f"""
        Current Market Data (XAU/USD): {market_data}
        
        User Query: {prompt}
        """
        print(f"Found Market Data: {market_data}")
    else:
        print("Warning: No live market data found in Redis. Answering based on internal knowledge only.")

    try:
        print(f"Generating response for: '{prompt}'...")
        response = await client.client.aio.models.generate_content(
            model=client.model_id,
            contents=enhanced_prompt
        )
        print("\n--- Response ---\n")
        print(response.text)
        print("\n----------------\n")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Query Gemini AI")
    parser.add_argument("prompt", nargs="?", help="The prompt to send to Gemini")
    args = parser.parse_args()

    try:
        client = GeminiClient()
        print(f"Connected to Gemini. Model: {client.model_id}")
    except Exception as e:
        print(f"Failed to initialize GeminiClient: {e}")
        return

    if args.prompt:
        await process_prompt(client, args.prompt)
    else:
        print("Enter prompts below (type 'exit' or 'quit' to stop):")
        while True:
            try:
                user_input = input("> ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                if not user_input.strip():
                    continue
                await process_prompt(client, user_input)
            except KeyboardInterrupt:
                break
            except EOFError:
                break

if __name__ == "__main__":
    asyncio.run(main())
