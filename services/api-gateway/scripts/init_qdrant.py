"""
Initialize Qdrant vector database collections.

This script creates the necessary Qdrant collections for:
- candle_embeddings: Vector embeddings of historical price patterns

Usage:
    python scripts/init_qdrant.py
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams


def init_qdrant_collections():
    """Create Qdrant collections for the MTF Trading System."""

    # Connect to Qdrant
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=qdrant_url)

    print(f"🔗 Connecting to Qdrant at {qdrant_url}...")

    # Collection: candle_embeddings
    # Purpose: Store embeddings of historical price patterns for similarity search
    # Use case: AI Analyst retrieval, pattern matching
    collection_name = "candle_embeddings"
    vector_size = 768  # Standard size for sentence-transformers models (e.g., all-MiniLM-L6-v2)
                       # Adjust if using different embedding model or Gemini embeddings

    try:
        # Check if collection already exists
        collections = client.get_collections().collections
        existing_names = [col.name for col in collections]

        if collection_name in existing_names:
            print(f"⚠️  Collection '{collection_name}' already exists. Skipping creation.")
            return

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE  # Cosine similarity for semantic search
            )
        )

        print(f"✅ Successfully created collection: {collection_name}")
        print(f"   - Vector size: {vector_size}")
        print(f"   - Distance metric: COSINE")

        # Verify collection
        collection_info = client.get_collection(collection_name)
        print(f"\n📊 Collection info:")
        print(f"   - Vectors count: {collection_info.vectors_count}")
        print(f"   - Points count: {collection_info.points_count}")

    except Exception as e:
        print(f"❌ Error initializing Qdrant collections: {e}")
        raise


if __name__ == "__main__":
    print("🌱 Initializing Qdrant collections...")
    init_qdrant_collections()
    print("\n✨ Qdrant initialization complete!")
