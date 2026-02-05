import asyncio
import sys
import argparse
import aiohttp
from pathlib import Path

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.agents.daily_briefing import DailyBriefingAgent
from app.core.config import settings

async def get_auth_token(username, password):
    """Authenticates to get a Bearer token."""
    base_url = settings.API_GATEWAY_URL
    
    async with aiohttp.ClientSession() as session:
        # 1. Try Login
        try:
            async with session.post(f"{base_url}/api/v1/auth/token", data={"username": username, "password": password}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return f"Bearer {data['auth']['access_token']}"
        except Exception as e:
            print(f"⚠️  Auth Connection Warning: {e}")
            return None

        # 2. If Login failed and user is ai_analyst, Try Register
        if username == "ai_analyst":
            try:
                print("Registering new AI Analyst user...")
                async with session.post(f"{base_url}/api/v1/auth/register", json={"username": username, "password": password, "email": "ai@mtf.system"}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return f"Bearer {data['auth']['access_token']}"
                    else:
                        print(f"❌ Registration failed: {await resp.text()}")
            except Exception as e:
                 print(f"❌ Registration Connection Error: {e}")
        else:
             print(f"❌ Login failed for {username}. Not attempting auto-registration for non-system user.")
    
    return None

async def check_account_setup(token: str, username: str):
    """Checks the user's Fund and Broker Account. Auto-creates Mock for ai_analyst only."""
    headers = {"Authorization": token}
    base_url = settings.API_GATEWAY_URL
    async with aiohttp.ClientSession() as session:
        # 1. Check/Create Fund
        fund_id = None
        try:
            async with session.get(f"{base_url}/api/v1/funds", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    funds = data.get("data", [])
                    if funds:
                        fund_id = funds[0]["id"]
                        # print(f"✅ Found existing fund: {funds[0]['name']}")
                    elif username == "ai_analyst":
                        print("Creating new fund 'AI Capital'...")
                        payload = {"name": "AI Capital", "description": "AI Managed Fund"}
                        async with session.post(f"{base_url}/api/v1/funds", json=payload, headers=headers) as f_resp:
                            if f_resp.status == 201:
                                f_data = await f_resp.json()
                                fund_id = f_data["data"]["id"]
                                print("✅ Fund created.")
                            else:
                                print(f"❌ Failed to create fund: {await f_resp.text()}")
                                return
                    else:
                        print(f"⚠️  No funds found for {username}. Please create a fund via the dashboard.")
                        return
        except Exception as e:
            print(f"❌ Fund Check Error: {e}")
            return

        if not fund_id:
            return

        # 2. Check/Create Broker Account
        try:
            async with session.get(f"{base_url}/api/v1/accounts/", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    accounts = data.get("data", [])
                    if accounts:
                        print(f"✅ Active Broker Account: {accounts[0]['broker_name']} ({accounts[0]['account_name']})")
                    elif username == "ai_analyst":
                        print("Creating MOCK broker account...")
                        # Use MOCK broker as identified in factory.py
                        payload = {
                            "fund_id": fund_id,
                            "broker_name": "MOCK",
                            "account_name": "AI Paper Trading",
                            "credentials": {"api_key": "mock_key", "account_id": "mock_id"},
                            "is_live": False
                        }
                        async with session.post(f"{base_url}/api/v1/accounts/", json=payload, headers=headers) as a_resp:
                            if a_resp.status == 201:
                                print("✅ Mock Account created.")
                            else:
                                print(f"❌ Failed to create mock account: {await a_resp.text()}")
                    else:
                        print(f"⚠️  No broker accounts found for {username}. Please connect cTrader or Oanda.")

        except Exception as e:
            print(f"❌ Account Check Error: {e}")

async def main():
    parser = argparse.ArgumentParser(description="Generate Daily Briefing")
    parser.add_argument("--prompt", type=str, default="Generate a daily trading briefing.", help="Custom instruction for the briefing")
    parser.add_argument("--username", type=str, default="ai_analyst", help="Username to login with")
    parser.add_argument("--password", type=str, default="password123", help="Password for login")
    args = parser.parse_args()

    print("☀️  Starting Daily Briefing Agent...")
    print(f"Goal: {args.prompt}\n")
    
    # Get Auth Token
    auth_header = await get_auth_token(args.username, args.password)
    if auth_header:
        print(f"✅ Authenticated as '{args.username}'")
        await check_account_setup(auth_header, args.username)
    else:
        print("⚠️  Proceeding without Authentication (some tools may fail)")

    try:
        agent = DailyBriefingAgent()
        print("✅ Agent Initialized. Gathering Intelligence...")
        
        report = await agent.run(input_text=args.prompt, auth_header=auth_header)
        
        print("\n" + "="*40)
        print("       DAILY BRIEFING REPORT")
        print("="*40 + "\n")
        print(report)
        print("\n" + "="*40 + "\n")

    except Exception as e:
        print(f"❌ Error generating briefing: {e}")
        # print specific help if it looks like a connection error
        if "Connection refused" in str(e) or "NewConnectionError" in str(e):
             print("\n💡 Tip: Ensure backend services are running to fetch data:")
             print("   docker compose up -d api-gateway strategy-core execution")

if __name__ == "__main__":
    asyncio.run(main())
