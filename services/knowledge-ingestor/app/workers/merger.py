from __future__ import annotations
import asyncio
from datetime import datetime
from app.core.app_config import config
from app.core.logger import get_logger
from app.tools.falkordb_client import FalkorDBClient

logger = get_logger("MarketMerger")


class MarketMerger:
    """
    Worker for merging disparate market data into the FalkorDB Knowledge Graph.
    This fulfills Phase 9.2: Knowledge-Driven Intelligence.
    """

    def __init__(self):
        self.client = FalkorDBClient(
            host=config.falkor_host,
            port=config.falkor_port,
            graph_name=config.graph_name,
        )
        self.is_running = False

    async def seed_baseline(self):
        """Seed the graph with basic Symbol and Asset hierarchy."""
        logger.info("🌱 Seeding Phase 9 Knowledge Baseline...")

        queries = [
            # Symbols
            "MERGE (s:Symbol {name: 'XAUUSD'}) SET s.base = 'XAU', s.quote = 'USD', s.category = 'Commodity'",
            "MERGE (s:Symbol {name: 'EURUSD'}) SET s.base = 'EUR', s.quote = 'USD', s.category = 'Forex'",
            "MERGE (s:Symbol {name: 'BTCUSD'}) SET s.base = 'BTC', s.quote = 'USD', s.category = 'Crypto'",
            # Assets
            "MERGE (a:Asset {name: 'Gold'}) SET a.category = 'Precious Metals', a.safe_haven = true",
            "MERGE (a:Asset {name: 'Euro'}) SET a.category = 'Fiat', a.issuer = 'ECB'",
            "MERGE (a:Asset {name: 'Bitcoin'}) SET a.category = 'Digital Asset', a.scarcity = 'High'",
            # Relationships
            "MATCH (s:Symbol {name: 'XAUUSD'}), (a:Asset {name: 'Gold'}) MERGE (s)-[:REPRESENTS]->(a)",
            "MATCH (s:Symbol {name: 'EURUSD'}), (a:Asset {name: 'Euro'}) MERGE (s)-[:REPRESENTS]->(a)",
            "MATCH (s:Symbol {name: 'BTCUSD'}), (a:Asset {name: 'Bitcoin'}) MERGE (s)-[:REPRESENTS]->(a)",
        ]

        try:
            result = await asyncio.to_thread(self.client.execute_batch, queries)
            logger.info(
                f"✅ Baseline Seeded: {result.get('success', 0)} queries successful."
            )
        except Exception as e:
            logger.error(f"❌ Seeding Failed: {e}")

    async def merge_market_sentiment(self):
        """
        Periodically merge sentiment and context data.
        In Phase 9.2, this links Symbols to top-level 'MarketContext' nodes.
        """
        logger.info("🔄 Running Market Sentiment Merger...")

        # Mock Context (In 9.3 this comes from News/LLM)
        contexts = [
            {
                "symbol": "XAUUSD",
                "summary": "Gold remains a preferred safe haven amid geopolitical tensions and central bank accumulation.",
                "score": 1.2,
            },
            {
                "symbol": "BTCUSD",
                "summary": "Bitcoin showing positive momentum following ETF inflows and institutional adoption.",
                "score": 1.5,
            },
        ]

        for ctx in contexts:
            now_str = datetime.now().isoformat()
            ctx_id = f"ctx_{ctx['symbol']}_{datetime.now().strftime('%Y%m%d')}"

            query = f"""
            MATCH (s:Symbol {{name: '{ctx["symbol"]}'}})
            MERGE (c:Context {{id: '{ctx_id}'}})
            ON CREATE SET 
                c.summary = '{ctx["summary"]}',
                c.knowledge_score = {ctx["score"]},
                c.timestamp = '{now_str}'
            MERGE (s)-[:HAS_CONTEXT]->(c)
            """
            try:
                await asyncio.to_thread(self.client.execute_query, query)
                logger.debug(f"✅ Merged context for {ctx['symbol']}")
            except Exception as e:
                logger.error(f"❌ Failed to merge context for {ctx['symbol']}: {e}")

    async def run_loop(self):
        """Main worker loop."""
        self.is_running = True
        logger.info("🚀 Market Merger Worker Started.")

        # Initial Seed
        await self.seed_baseline()

        while self.is_running:
            try:
                await self.merge_market_sentiment()
                # Run every 30 minutes in Phase 9
                await asyncio.sleep(1800)
            except Exception as e:
                logger.error(f"Error in Merger Loop: {e}")
                await asyncio.sleep(60)


async def start_merger_worker():
    """Entry point for main.py."""
    merger = MarketMerger()
    await merger.run_loop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(start_merger_worker())
