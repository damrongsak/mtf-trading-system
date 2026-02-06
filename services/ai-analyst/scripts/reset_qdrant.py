import asyncio
import sys
from pathlib import Path
from qdrant_client import QdrantClient

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings

def main():
    print("🧹 Resetting Qdrant Collections...")
    
    try:
        qdrant = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
            https=settings.QDRANT_GRPC_HTTPS
        )
        
        collections = ["system_docs", "strategies", "journal_entries"]
        
        for c in collections:
            print(f"   Deleting {c}...")
            qdrant.delete_collection(c)
            print(f"   ✅ Deleted {c}")

        print("\n✨ All collections reset. They will be recreated on next usage.")

    except Exception as e:
        print(f"❌ Failed to reset Qdrant: {e}")

if __name__ == "__main__":
    main()
