
import asyncio
import aiohttp
import json

async def test_responses_api():
    url = "http://host.docker.internal:18789/v1/responses"
    token = "9b0cb07e142a651540bf2659bb8663ea62641504e8d81309"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # OpenResponses Payload
    payload = {
        "items": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "text", "text": "Say hello world"}]
            }
        ],
        "model": "agent:main",
        "sessionKey": "test-zero-cost",
        "stream": False
    }
    
    print(f"Testing POST {url}...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(json.dumps(data, indent=2))
                else:
                    text = await resp.text()
                    print(f"Error Response: {text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_responses_api())
