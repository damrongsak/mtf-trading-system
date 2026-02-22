import asyncio
import os
import sys
import json
from datetime import datetime

# Add app to path
if os.path.exists("/app/app"):
    sys.path.append("/app")
else:
    sys.path.append(os.path.join(os.getcwd(), "services/ai-analyst"))

from app.tools.open_interest import OpenInterestTool
from app.core.config import settings

async def verify():
    tool = OpenInterestTool()
    auth_token = os.getenv("AUTH_TOKEN")
    import traceback
    
    for horizon in [None, "short", "long"]:
        try:
            print(f"\n--- Testing {horizon if horizon else 'Universal'} Horizon Report ---")
            result = await tool.run(input_data={"symbol": "XAUUSD", "horizon": horizon}, auth_token=auth_token)
            print(result)
        except Exception:
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
