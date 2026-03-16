import sys
from app.tools.falkordb_client import FalkorDBClient
from app.core.app_config import config

def check_db():
    print(f"Connecting to FalkorDB at {config.falkor_host}:{config.falkor_port}...")
    client = FalkorDBClient(config.falkor_host, config.falkor_port, config.graph_name)
    result = client.connect()
    
    if result.get("status") == "connected":
        print("✅ Connected successfully!")
        stats = client.get_stats()
        if stats.get("status") == "success":
            print(f"Graph Info: {stats.get('info')}")
        else:
            print(f"❌ Failed to get graph info: {stats.get('message')}")
    else:
        print(f"❌ Connection failed: {result.get('message')}")

if __name__ == "__main__":
    check_db()
