import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.rag import RAGService
from app.services.gemini import GeminiClient

async def test_expansion():
    print("🔍 Testing Context Expansion (Parent Retrieval)...\n")
    
    try:
        gemini = GeminiClient()
        rag = RAGService(gemini)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        return

    query = "Kelly Criterion formula and its dangers"
    
    print(f"❓ Query: {query}")
    print("Searching with expand_context=True...")
    print("-" * 50)
    
    results = await rag.search_library(query, limit=1, expand_context=True)
    
    if not results:
        print("⚠️ No results found.")
    else:
        res = results[0]
        print(f"Source: {res['filename']} (Chunk {res['metadata']['chunk_index']})")
        print(f"Content Length: {len(res['content'])} characters")
        print("\n--- CONTENT (Expanded) ---")
        print(res['content'][:1500] + "...")
        print("-" * 50)
        
    print("\nComparing with expand_context=False...")
    results_no_expand = await rag.search_library(query, limit=1, expand_context=False)
    if results_no_expand:
        res_ne = results_no_expand[0]
        print(f"Content Length (No Expand): {len(res_ne['content'])} characters")
        print(f"Difference: {len(res['content']) - len(res_ne['content'])} characters added.")

if __name__ == "__main__":
    asyncio.run(test_expansion())
