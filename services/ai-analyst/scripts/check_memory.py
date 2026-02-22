import asyncio
import os
import sys

# Add app to path
sys.path.insert(0, "/app")

from qdrant_client import QdrantClient
from app.core.config import settings

def main():
    qdrant = QdrantClient(host=settings.qdrant.host, port=settings.qdrant.port, api_key=settings.qdrant.api_key, https=settings.qdrant.grpc_https)
    user_id = "93cb8075-0e29-47f9-a939-8f413fb1dac4"  # Extracted from earlier chat logs
    coll = "user_memory"
    
    try:
        from qdrant_client.http import models
        search_filter = models.Filter(must=[models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id))])
        
        # We just query all points by scrolling or searching with a dummy query
        hits = qdrant.scroll(collection_name=coll, scroll_filter=search_filter, limit=10)
        
        print("\n--- User Memory Store ---")
        points, next_page = hits
        if not points:
             print("No facts found for user.")
        for p in points:
             print(f"Fact: {p.payload.get('content')}")
        print("-------------------------\n")
    except Exception as e:
        print(f"Error querying Qdrant: {e}")

if __name__ == "__main__":
    main()
