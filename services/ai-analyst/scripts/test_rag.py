import asyncio
import sys
from pathlib import Path
import logging

# Add parent dir to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.gemini import GeminiClient
from app.services.rag import RAGService

# Configure Logging
logging.basicConfig(level=logging.ERROR)

async def main():
    print("🧪 Testing RAG Service (Ingest & Retrieve)...\n")
    
    try:
        # 1. Initialize
        print("1. Connecting to Services...")
        gemini = GeminiClient()
        rag = RAGService(gemini_client=gemini)
        print("✅ Connected to Gemini & Qdrant.")

        # 2. Ingest Sample Doc
        doc_filename = "trading_rules_v1.md"
        doc_content = """
        # MTF Olympus Trading Rules
        1. Always risking 1% per trade.
        2. Never trade 15 minutes before High Impact News.
        3. Gold (XAUUSD) is the primary asset.
        4. Use EMA 200 for Macro Bias.
        """
        print(f"\n2. Ingesting System Document: {doc_filename}...")
        await rag.ingest_document(doc_filename, doc_content, doc_type="rules")
        print("✅ Document Ingested.")

        # 3. Ingest Sample Strategy
        strat_id = "strat_test_001"
        strat_code = """
        class RsiStrategy(SandboxedStrategy):
            def run(self, data):
                rsi = vbt.RSI.run(data.close, window=14)
                entries = rsi.rsi_below(30)
                exits = rsi.rsi_above(70)
                return vbt.Portfolio.from_signals(data.close, entries, exits)
        """
        user_id = "trader1"
        print(f"\n3. Ingesting Strategy: {strat_id}...")
        await rag.ingest_strategy(strat_id, strat_code, user_id=user_id, stats={"sharpe": 1.5})
        print("✅ Strategy Ingested.")

        # 4. Test Retrieval (Docs)
        query = "What is the risk per trade?"
        print(f"\n4. Testing Doc Search: '{query}'...")
        docs = await rag.search_documentation(query, limit=1)
        if docs:
            print(f"   🔹 Match Found: {docs[0]['filename']}")
            print(f"   🔹 Snippet: {docs[0]['content'][:100]}...")
            print(f"   🔹 Score: {docs[0]['score']}")
        else:
            print("   ❌ No documents found.")

        # 5. Test Retrieval (Strategy)
        query_strat = "RSI mean reversion code"
        print(f"\n5. Testing Strategy Search: '{query_strat}'...")
        strats = await rag.search_similar_strategies(query_strat, user_id=user_id, limit=1)
        if strats:
            print(f"   🔹 Strategy Found (Score: {strats[0]['score']})")
            print(f"   🔹 Code Snippet:\n{strats[0]['code'][:100]}...")
        else:
            print("   ❌ No strategies found.")

    except Exception as e:
        print(f"\n❌ Retrieval Test Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
