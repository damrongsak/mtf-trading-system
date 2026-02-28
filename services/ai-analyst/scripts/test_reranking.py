import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService
from app.services.gemini import GeminiClient

async def test_reranking():
    print("🔍 Testing Gemini Reranking (Cross-Encoder)...\n")
    
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    # Use a query where the top dense hit might be less relevant than a slightly lower one
    query = "What is the specific formula for the Kelly Criterion in trading?"
    
    print(f"❓ Query: {query}")
    print("-" * 50)
    
    results = await rag.search_library(query, limit=10)
    
    if not results:
        print("⚠️ No results found.")
    else:
        print(f"Top 5 after Reranking:")
        for i, res in enumerate(results[:5]):
            print(f"[{i+1}] Source: {res['filename']} (Score: {res['score']:.4f})")
            print(f"Content: {res['content'][:300]}...")
            print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_reranking())
