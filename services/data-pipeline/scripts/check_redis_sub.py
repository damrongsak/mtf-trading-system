
import asyncio
import redis.asyncio as redis
import os
import json

# Redis Config
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

async def listen_to_stream():
    print(f"Connecting to Redis at {REDIS_URL}...")
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        
        # Subscribe to all market data channels
        pattern = "market_data:*"
        await pubsub.psubscribe(pattern)
        
        print(f"Subscribed to '{pattern}'. Listening for 10 seconds...")
        
        start_time = asyncio.get_event_loop().time()
        
        while True:
            # Timeout after 10 seconds
            if asyncio.get_event_loop().time() - start_time > 10:
                print("Timeout reached. Stopping listener.")
                break
                
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message:
                    channel = message['channel']
                    data = message['data']
                    print(f"\n[CHANNEL] {channel}")
                    try:
                        parsed = json.loads(data)
                        print(f"[DATA] {json.dumps(parsed, indent=2)}")
                    except:
                        print(f"[DATA] {data}")
            except asyncio.TimeoutError:
                continue
                
        await pubsub.close()
        await r.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(listen_to_stream())
