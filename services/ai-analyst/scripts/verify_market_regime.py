import asyncio
import aiohttp
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.tools.market_state import MarketStateTool

async def verify_strategy_core():
    print("\n--- 1. Testing Strategy Core API Direct ---")
    url = "http://strategy-core:8000/api/v1/market/regime"
    payload = {"symbol": "XAUUSD", "timeframe": "H1"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Response: {data}")
                    return True
                else:
                    print(f"Error: {await resp.text()}")
                    return False
        except Exception as e:
            print(f"Connection Failed: {e}")
            return False

async def verify_api_gateway():
    print("\n--- 2. Testing API Gateway Proxy ---")
    # Note: API Gateway is at http://api-gateway:8000 internally
    url = "http://api-gateway:8000/api/v1/analysis/market-regime/XAUUSD"
    params = {"timeframe": "H1"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print(f"Response: {data}")
                    return True
                else:
                    print(f"Error: {await resp.text()}")
                    return False
        except Exception as e:
            print(f"Connection Failed: {e}")
            return False

async def verify_ai_tool():
    print("\n--- 3. Testing AI Analyst Tool (MarketStateTool) ---")
    tool = MarketStateTool()
    
    # Mocking settings if needed, but BaseTool usually loads them.
    # We are running inside ai-analyst container usually.
    
    try:
        # Test 1: String Input
        print("Input: 'XAUUSD'")
        res1 = await tool.run("XAUUSD")
        print(f"Result:\n{res1}\n")
        
        # Test 2: Dict Input with Timeframe
        print("Input: {'symbol': 'XAUUSD', 'timeframe': 'H4'}")
        res2 = await tool.run({"symbol": "XAUUSD", "timeframe": "H4"})
        print(f"Result:\n{res2}\n")
        
        if "Adaptive Market State" in res1 and "Adaptive Market State" in res2:
            return True
        return False
        
    except Exception as e:
        print(f"Tool Execution Failed: {e}")
        return False

async def main():
    print("Starting End-to-End Verification for Adaptive Guardrails...")
    
    s1 = await verify_strategy_core()
    s2 = await verify_api_gateway()
    s3 = await verify_ai_tool()
    
    if s1 and s2 and s3:
        print("\n✅ VERIFICATION SUCCESS: All systems go.")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
