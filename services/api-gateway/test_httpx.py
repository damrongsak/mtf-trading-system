import httpx
import asyncio
import sys

async def main():
    url = "http://ai-analyst:8000/api/v1/ai/diagnose"
    headers = {
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0cmFkZXIxIiwiZXhwIjoxNzc1ODk4MDIyfQ.W4yjh2NWqX88FhHk-92nCpBCdpJB9tVJbC5HvnybnKs",
        "X-Request-ID": "test-request-id-123"
    }
    print(f"Testing httpx GET to {url} with headers...")
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            response = await client.get(url, headers=headers)
            print(f"Status: {response.status_code}")
            print(f"Body: {response.text[:200]}...")
    except Exception as e:
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
