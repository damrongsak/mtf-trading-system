import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService
from app.services.gemini import GeminiClient

async def test_retrieval():
    print("🔍 Testing retrieval from 'quant_library'...\n")
    
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    queries = [
        "What is the Kelly Criterion and how is it used in capital allocation for trading?",
        "Explain Institutional Gamma Walls and how they act as support or resistance.",
        "What are the key elements of Smart Money Concepts (SMC) in market structure analysis?"
    ]

    for query in queries:
        print(f"❓ Query: {query}")
        print("-" * 50)
        
        results = await rag.search_library(query, limit=3)
        
        if not results:
            print("⚠️ No results found.")
        else:
            for i, res in enumerate(results):
                print(f"[{i+1}] Source: {res['filename']} (Score: {res['score']:.4f})")
                print(f"Context: {res['content'][:500]}...")
                print("-" * 30)
        print("\n")

if __name__ == "__main__":
    asyncio.run(test_retrieval())
