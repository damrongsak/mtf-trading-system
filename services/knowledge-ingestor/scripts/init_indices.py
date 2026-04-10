import os
import sys
from typing import List

# Add app directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.tools.falkordb_client import FalkorDBClient
from app.core.app_config import config

def init_indices():
    """Create essential indices for Olympus Knowledge Graph"""
    client = FalkorDBClient(config.falkor_host, config.falkor_port, config.graph_name)
    client.connect()
    
    indices = [
        "CREATE INDEX FOR (n:Event) ON (n.name)",
        "CREATE INDEX FOR (n:Asset) ON (n.name)",
        "CREATE INDEX FOR (n:MacroIndicator) ON (n.name)",
        "CREATE INDEX FOR (n:Paper) ON (n.hash)",
        "CREATE INDEX FOR (n:Concept) ON (n.name)"
    ]
    
    print(f"--- Initializing Indices for {config.graph_name} ---")
    for idx_query in indices:
        print(f"Executing: {idx_query}")
        result = client.execute_query(idx_query)
        if result.get("status") == "success":
            print("  ✅ Success")
        else:
            msg = result.get("message", "Unknown error")
            if "Index already exists" in msg:
                 print("  ✅ Already exists")
            else:
                 print(f"  ❌ Failed: {msg}")

if __name__ == "__main__":
    init_indices()
