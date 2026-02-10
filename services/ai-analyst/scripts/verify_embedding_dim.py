
import asyncio
import os
import sys

# Add app to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.services.gemini import GeminiClient

async def main():
    try:
        if not settings.GOOGLE_API_KEY:
            print("API Key missing")
            return
        
        client = GeminiClient()
        # Use the same model as RAGService: models/gemini-embedding-001
        res = await client.client.aio.models.embed_content(
             model="models/gemini-embedding-001",
             contents="Hello World"
        )
        
        # Handle response structure
        emb = None
        if hasattr(res, 'embeddings') and res.embeddings:
            emb = res.embeddings[0].values
        elif hasattr(res, 'embedding'):
             emb = res.embedding
             
        if emb:
            print(f"Embedding Dimension: {len(emb)}")
        else:
            print("No embedding returned")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
