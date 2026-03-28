"""
Olympus Ingestor - Hierarchical 3-Tier Processing (REFACTORED)
Professional large file ingestion for financial news & analysis
"""

import json
import asyncio
import hashlib
import redis as redislib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Callable

from app.base_ingestor import BaseIngestor
from app.core.llm_utils import LLMUtils
from app.core.logger import get_logger
from app.core.semantic_chunker import SemanticChunker
from app.core.ontology import GraphExtractionSchema
from app.core.doc_analyzer import DocumentAnalyzer, DocStructure
from app.tools.market_reader import MarketReaderTool
from app.tools.web_search import WebSearchTool
from app.core.models import ChunkResult, HierarchicalResult

logger = get_logger("HierarchicalIngestor")

# ============================================================================
# PROMPT TEMPLATES (Optimized with JSON Schema & CoT)
# ============================================================================

TIER_SUMMARY_PROMPT = """You are THE EXECUTIVE SUMMARY EXPERT for Project Olympus.

GLOBAL CONTEXT:
Document Title: {doc_title}
Key Themes: {main_themes}
Anchor Entities: {key_entities}

Your mission: Extract key metadata and high-level context from the document's introduction.

Output format (Valid JSON only):
{{
  "reasoning": "Brief analysis of the introduction",
  "headlines": ["Lead headline", "Secondary event"],
  "tickers": ["XAUUSD", "BTC"],
  "sentiment": "bullish|bearish|neutral",
  "key_numbers": {{"label": value}},
  "source": "Source name",
  "timestamp": "YYYY-MM-DD",
  "cypher_queries": [
    "MERGE (p:Paper {{title: 'Doc Title', source: 'Source', date: 'Date', hash: 'HASH_PLACEHOLDER'}})",
    "MERGE (a:Asset {{name: 'XAUUSD', type: 'COMMODITY'}})"
  ]
}}"""


TIER_DETAIL_PROMPT = """You are THE KNOWLEDGE ARCHITECT for Project Olympus.

GLOBAL CONTEXT:
Document Title: {doc_title}
Key Themes: {main_themes}
Anchor Entities: {key_entities}

Your mission: Extract complex entities and relationships into valid Cypher queries based on the MAIN CONTENT.

OLYMPUS ONTOLOGY:
Nodes: 
  - Paper (Document)
  - Asset (e.g., XAUUSD, BTC, Brent Oil)
  - Concept (Theoretical ideas, e.g., Liquidity, Volatility)
  - MacroIndicator (e.g., CPI, Interest Rates, GDP)
  - Event (e.g., FOMC Meeting, Geopolitical conflict)
  - Strategy (Trading plans)
  - Organization (e.g., Fed, BlackRock, OPEC)
  - Country
  - Person
  - SMC_Pattern (Smart Money Concepts: OrderBlock, FairValueGap, LiquiditySweep, BreakOfStructure)
  - Timeframe (M1, M15, H1, H4, D1, W1)

Edges: 
  MENTIONS, INFLUENCES, SUPPORTS, CONTRADICTS, TRIGGERS, CORRELATES_WITH, 
  PROPOSES_STRATEGY, AFFECTS, LEADS_TO, OBSERVED_IN (for patterns in timeframes),
  HEDGE_AGAINST, LIQUIDATES

Output format (Valid JSON only):
{{
  "thought_process": "Professional analysis of identified entities and their structural links",
  "nodes": [{{ "label": "SMC_Pattern", "name": "H4 Order Block", "type": "BULLISH_OB" }}],
  "edges": [{{ "from": "H4 Order Block", "to": "XAUUSD", "type": "SUPPORTS" }}],
  "cypher_queries": [
    "MERGE (p:SMC_Pattern {{name: 'H4 Order Block', type: 'BULLISH_OB', confidence: 'high'}})",
    "MERGE (a:Asset {{name: 'XAUUSD'}})",
    "MATCH (p:SMC_Pattern {{name: 'H4 Order Block'}}), (a:Asset {{name: 'XAUUSD'}}) MERGE (p)-[:SUPPORTS {{context: 'Price rejection at support'}}]->(a)"
  ]
}}"""


TIER_CONCLUSION_PROMPT = """You are THE MARKET STRATEGIST for Project Olympus.

GLOBAL CONTEXT:
Document Title: {doc_title}
Key Themes: {main_themes}
Anchor Entities: {key_entities}

Your mission: Extract forward-looking predictions and actionable trading strategies.

Output format (Valid JSON only):
{{
  "strategy_logic": "Analysis of why these strategies are proposed",
  "predictions": [{{ "event": "Gold $3k", "probability": "HIGH", "timeline": "Q2 2026" }}],
  "strategies": [{{ "name": "Long Gold", "timeframe": "H4", "entry": 2850 }}],
  "risk_factors": ["inflation", "geopolitics"],
  "cypher_queries": [
    "MERGE (s:Strategy {{name: 'Long Gold', timeframe: 'H4'}})",
    "MERGE (e:Event {{name: 'Gold $3k Target', probability: 'HIGH'}})",
    "MATCH (s:Strategy {{name: 'Long Gold'}}), (e:Event {{name: 'Gold $3k Target'}}) CREATE (s)-[:PROPOSES_STRATEGY]->(e)"
  ]
}}"""


COMMITTER_PROMPT = """You are THE COMMITTER for Project Olympus.

Your role: Merge results from 3 tiers, deduplicate entities, and generate final clean Cypher queries.

DEDUPLICATION RULES:
1. Financial Synonyms: Merge "Fed" -> "Federal Reserve", "Gold" -> "XAUUSD", "BTC" -> "Bitcoin", "ECB" -> "European Central Bank".
2. Case Sensitivity: Treat "Interest Rates" and "interest rates" as the same entity.
3. Proper Names: Prefer full names over acronyms where possible.

RELATIONSHIP METADATA:
For EVERY relationship (edge), add the following properties if available:
- source_ref: Filename or URL
- confidence: high|medium|low
- extracted_at: Current ISO timestamp

Output format (Valid JSON only):
{
  "merge_notes": "Summary of deduplication and conflicts resolved",
  "final_nodes": ["NodeName1", "NodeName2"],
  "final_edges": ["Node1 -> Node2"],
  "cypher_queries": [
     "MATCH (n) ...",
     "MERGE (n:Asset {name: 'Gold'})-[:INFLUENCES {source_ref: 'doc.pdf', confidence: 'high', extracted_at: '...'}]->(m:MacroIndicator {name: 'Inflation'})"
  ],
  "deduplication_stats": {
    "nodes_removed": 5,
    "edges_removed": 3
  }
}"""

WEBSCOUT_PROMPT = """You are THE WEBSCOUT AGENT for Project Olympus.

Your role: Review the extracted knowledge and identify exactly 1-3 HIGH-IMPACT entities or events that need live web verification (e.g., breaking news, current prices, recent geopolitical shifts).

IMPORTANT: Use the ACTUAL names of the entities found in the document. DO NOT use placeholders like "[Entity]" or "[Asset]".

Output format (Valid JSON only):
{
  "search_required": true,
  "reasoning": "Why we need to search",
  "queries": [
    "Latest news on Microsoft performance",
    "Current supply chain status of TSMC"
  ]
}"""


class HierarchicalIngestor(BaseIngestor):
    """3-Tier Hierarchical Ingestion for Large Financial Documents"""
    
    def __init__(self):
        super().__init__("OlympusHierarchicalIngestor")
        self.summary_chars = 2000
        self.detail_chars = 60_000
        self.conclusion_chars = 3000
        self.semantic_chunker = SemanticChunker(chunk_size=12000, chunk_overlap=1000)

    def _make_publisher(self, task_id: str | None) -> Callable:
        """
        Returns a publish(stage, **kwargs) function that sends JSON progress
        events to Redis channel `progress:{task_id}`.
        Creates one Redis connection per pipeline run (cheap, sync).
        If task_id is None, returns a no-op.
        """
        if not task_id:
            return lambda stage, **kw: None
        try:
            r = redislib.Redis(
                host=config.falkor_host,
                port=config.falkor_port,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            r.ping()  # Verify connection immediately
            self.logger.info(f"📡 Redis progress publisher ready for {task_id}")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Redis for progress tracking: {e}")
            return lambda stage, **kw: None

        def publish(stage: str, **kwargs) -> None:
            try:
                payload = json.dumps({
                    "stage": stage,
                    "task_id": task_id,
                    "ts": datetime.now().isoformat(),
                    **kwargs,
                })
                r.publish(f"progress:{task_id}", payload)
            except Exception as e:
                self.logger.warning(f"⚠️ Progress publish failed ({stage}) for {task_id}: {e}")

        return publish
    
    def read_file_tiers(self, path: Path) -> Dict[str, Any]:
        """Read file and split into 3 tiers (supports PDF and text)"""
        if path.suffix.lower() == '.pdf':
            self.logger.info(f"📄 Extracting PDF content from {path.name}")
            import pypdf
            try:
                reader = pypdf.PdfReader(path)
                full_content = ""
                for page in reader.pages:
                    full_content += page.extract_text() + "\n"
            except Exception as e:
                self.logger.error(f"Failed to read PDF {path.name}: {e}")
                raise
        else:
            with open(path, 'r', encoding='utf-8') as f:
                full_content = f.read()
        
        file_size = len(full_content)
        tiers = {}
        metadata = {"filename": path.name, "original_size": file_size, "tier_sizes": {}}
        
        summary_size = min(self.summary_chars, int(file_size * 0.1))
        tiers["summary"] = full_content[:summary_size]
        metadata["tier_sizes"]["summary"] = summary_size
        
        detail_start = int(file_size * 0.1)
        detail_end = int(file_size * 0.9)
        detail_content = full_content[detail_start:detail_end]
        
        if len(detail_content) > self.detail_chars:
            chunks = self.semantic_chunker.split_text(detail_content)
            tiers["detail"] = chunks
            metadata["tier_sizes"]["detail"] = len(detail_content)
            metadata["detail_chunks"] = len(chunks)
        else:
            tiers["detail"] = detail_content
            metadata["tier_sizes"]["detail"] = len(detail_content)
        
        conclusion_size = min(self.conclusion_chars, int(file_size * 0.1))
        tiers["conclusion"] = full_content[-conclusion_size:]
        metadata["tier_sizes"]["conclusion"] = conclusion_size
        
        return {"tiers": tiers, "metadata": metadata}
    
    def _calculate_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    async def process_tier_summary(self, content: str, doc_analysis: DocStructure) -> ChunkResult:
        """Tier 1: Executive Summary with Structural Context"""
        prompt = TIER_SUMMARY_PROMPT.format(
            doc_title=doc_analysis.title,
            main_themes=", ".join(doc_analysis.main_themes),
            key_entities=", ".join(doc_analysis.key_entities)
        )
        result = await LLMUtils.call_llm(prompt, content, "summary", max_tokens=2000)
        queries = result.get("cypher_queries", [])
        return ChunkResult(
            tier="summary",
            cypher_queries=queries,
            node_count=len(result.get("tickers", [])) + len(result.get("key_numbers", {})),
            edge_count=len(queries),
            raw_response=str(result)[:500]
        )
    
    async def process_tier_detail(self, content: str | List[str], doc_analysis: DocStructure) -> ChunkResult:
        """Tier 2: Full Content Details with Structured Schema Enforcement & Context"""
        all_queries = []
        node_count = 0
        edge_count = 0
        
        prompt = TIER_DETAIL_PROMPT.format(
            doc_title=doc_analysis.title,
            main_themes=", ".join(doc_analysis.main_themes),
            key_entities=", ".join(doc_analysis.key_entities)
        )
        
        chunks = content if isinstance(content, list) else [content]
        
        for i, chunk in enumerate(chunks):
            try:
                # Use instructor-powered structured extraction
                structured_data = await LLMUtils.call_llm_structured(
                    system_prompt=prompt,
                    user_prompt=chunk,
                    response_model=GraphExtractionSchema,
                    tier="detail_structured"
                )
                
                # Convert validated schema to Cypher
                queries = structured_data.to_cypher()
                all_queries.extend(queries)
                node_count += len(structured_data.nodes)
                edge_count += len(structured_data.relationships)
                
            except Exception as e:
                self.logger.error(f"❌ Detail Ingestion failed for chunk {i}: {e}")
                # Fallback to basic JSON call if structured fails (best effort)
                result = await LLMUtils.call_llm(TIER_DETAIL_PROMPT, chunk, "detail_fallback", max_tokens=8000)
                all_queries.extend(result.get("cypher_queries", []))

        return ChunkResult(tier="detail", cypher_queries=all_queries, node_count=node_count, edge_count=edge_count)
    
    async def process_tier_conclusion(self, content: str, doc_analysis: DocStructure) -> ChunkResult:
        """Tier 3: Conclusion & Predictions with Structural Context"""
        prompt = TIER_CONCLUSION_PROMPT.format(
            doc_title=doc_analysis.title,
            main_themes=", ".join(doc_analysis.main_themes),
            key_entities=", ".join(doc_analysis.key_entities)
        )
        result = await LLMUtils.call_llm(prompt, content, "conclusion", max_tokens=3000)
        queries = result.get("cypher_queries", [])
        return ChunkResult(
            tier="conclusion",
            cypher_queries=queries,
            node_count=len(result.get("predictions", [])) + len(result.get("strategies", [])),
            edge_count=len(queries)
        )
    
    async def process_committer(self, results: List[ChunkResult], filename: str) -> Dict[str, Any]:
        """Merge all tiers and prepare final queries, with real-time enrichment"""
        all_queries = []
        for r in results:
            all_queries.extend(r.cypher_queries)
        
        merge_input = f"""Source file: {filename}
Results from all tiers:
{json.dumps([{"tier": r.tier, "queries": r.cypher_queries[:10]} for r in results], indent=2)}
Total queries to merge: {len(all_queries)}
"""
        result = await LLMUtils.call_llm(COMMITTER_PROMPT, merge_input, tier="committer", max_tokens=4000)
        final_queries = result.get("cypher_queries", all_queries)
        
        return {
            "final_queries": final_queries,
            "stats": result.get("deduplication_stats", {}),
            "total_queries": len(all_queries),
            "final_nodes": result.get("final_nodes", []),
            "merge_notes": result.get("merge_notes", "")
        }
    
    async def enrich_with_intelligence(self, committer_result: Dict[str, Any]) -> List[str]:
        """Unified Intelligence Layer: Web Research + Market Data Enrichment"""
        enrichment_queries = []
        
        # --- Part 1: Real-Time Market Discovery (Phase 7) ---
        assets_to_check = {
            "Gold": ["Gold", "XAU", "XAUUSD"],
            "Bitcoin": ["Bitcoin", "BTC", "BTCUSD"],
            "Silver": ["Silver", "XAG", "XAGUSD"]
        }
        combined_nodes = [n.lower() for n in committer_result.get("final_nodes", [])]
        
        for asset_canonical, aliases in assets_to_check.items():
            if any(alias.lower() in combined_nodes for alias in aliases):
                price = MarketReaderTool.get_spot_price(asset_canonical)
                if price:
                    self.logger.info(f"✨ Market Enrichment: {asset_canonical} -> ${price}")
                    now_str = datetime.now().isoformat()
                    enrichment_queries.append(f"""
                        MERGE (a:Asset {{name: '{asset_canonical}'}})
                        SET a.real_time_price = {price}, a.last_market_sync = '{now_str}', a.status = 'ENRICHED'
                    """)

        # --- Part 2: WebScout Event Discovery (Phase 11) ---
        scout_input = f"Extracted Nodes: {committer_result.get('final_nodes')}\nMerge Notes: {committer_result.get('merge_notes')}"
        scout_report = await LLMUtils.call_llm(WEBSCOUT_PROMPT, scout_input, tier="web_scout", max_tokens=1000)
        
        if scout_report.get("search_required") and scout_report.get("queries"):
            for query in scout_report["queries"]:
                self.logger.info(f"🕵️ WebScout investigating: '{query}'")
                live_data = await WebSearchTool.search_and_summarize(query)
                safe_data = live_data.replace("'", "\\'").replace("\n", "\\n")
                now_str = datetime.now().isoformat()
                
                enrichment_queries.append(f"""
                    MERGE (w:WebIntelligence {{query: '{query.replace("'", "\\'")}'}})
                    SET w.content = '{safe_data}', w.last_updated = '{now_str}', w.source = 'DuckDuckGo_Live'
                """)
                
                # Link discovery to relevant context
                for node_name in committer_result.get("final_nodes", []):
                    if node_name.lower() in query.lower():
                        enrichment_queries.append(f"MATCH (n), (w:WebIntelligence {{query: '{query.replace("'", "\\'")}'}}) WHERE n.name = '{node_name}' MERGE (n)-[:HAS_LIVE_CONTEXT]->(w)")
                        
        return enrichment_queries

    async def run_pipeline(self, file_path: Path, task_id: str | None = None) -> HierarchicalResult:
        """Execute the full 3-tier pipeline with incremental sync check"""
        import time
        start_time = time.time()
        publish = self._make_publisher(task_id)
        
        # Read content first for hashing
        if file_path.suffix.lower() == '.pdf':
            import pypdf
            try:
                reader = pypdf.PdfReader(file_path)
                full_content = "\n".join([page.extract_text() for page in reader.pages])
            except Exception as e:
                self.logger.error(f"Failed to read PDF {file_path.name}: {e}")
                raise
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                full_content = f.read()
        
        content_hash = self._calculate_hash(full_content)
        
        # Check if already exists in FalkorDB
        if self.client.check_content_exists(content_hash):
            self.logger.info(f"⏭️ Skipping {file_path.name} (Hash already exists: {content_hash})")
            publish("skipped", filename=file_path.name, reason="Hash already exists")
            return HierarchicalResult(
                filename=file_path.name,
                status="complete",
                summary_queries=[],
                detail_queries=[],
                conclusion_queries=[],
                committer_result={"merge_notes": "Skipped due to existing hash"},
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        # 1. Structural Analysis
        doc_analysis = await DocumentAnalyzer.analyze(full_content[:15000])
        self.logger.info(f"🧠 Global Context Acquired: {doc_analysis.title}")
        publish("doc_analysis_done", title=doc_analysis.title, themes=doc_analysis.main_themes[:5])

        file_data = self.read_file_tiers(file_path)

        publish("summary_start", chars=len(file_data["tiers"]["summary"]))
        summary_task = self.process_tier_summary(file_data["tiers"]["summary"], doc_analysis)

        detail_content = file_data["tiers"]["detail"]
        detail_chunks = len(detail_content) if isinstance(detail_content, list) else 1
        publish("detail_start", chunks=detail_chunks)
        detail_task = self.process_tier_detail(detail_content, doc_analysis)

        publish("conclusion_start", chars=len(file_data["tiers"]["conclusion"]))
        conclusion_task = self.process_tier_conclusion(file_data["tiers"]["conclusion"], doc_analysis)

        results = await asyncio.gather(summary_task, detail_task, conclusion_task)
        publish("summary_done", queries=len(results[0].cypher_queries))
        publish("detail_done", queries=len(results[1].cypher_queries))
        publish("conclusion_done", queries=len(results[2].cypher_queries))

        publish("committer_start")
        commit_result = await self.process_committer(results, file_path.name)
        publish("committer_done", final_nodes=len(commit_result.get("final_nodes", [])))
        
        # Intelligence Layer (Market + Web)
        publish("enrichment_start")
        web_queries = await self.enrich_with_intelligence(commit_result)
        final_queries = commit_result["final_queries"] + web_queries
        
        # Execute to FalkorDB
        # Replace hash placeholders with actual hash
        final_queries = []
        for q in (commit_result["final_queries"] + web_queries):
            final_queries.append(q.replace("HASH_PLACEHOLDER", content_hash))
            
        exec_result = self.execute_to_falkor(final_queries)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        combined_committer_result = {**commit_result, **exec_result}
        status = "complete" if exec_result.get("success", 0) > 0 else "failed"

        publish(
            "pipeline_done" if status == "complete" else "pipeline_failed",
            nodes=exec_result.get("success", 0),
            total_queries=len(final_queries),
            elapsed_ms=elapsed_ms,
        )

        return HierarchicalResult(
            filename=file_path.name,
            status=status,
            summary_queries=results[0].cypher_queries,
            detail_queries=results[1].cypher_queries,
            conclusion_queries=results[2].cypher_queries,
            committer_result=combined_committer_result,
            processing_time_ms=elapsed_ms,
            total_nodes=exec_result.get("success", sum(r.node_count for r in results)),
            total_edges=exec_result.get("total", sum(r.edge_count for r in results)) - exec_result.get("success", 0)
        )

    async def run_pipeline_on_text(self, text: str, filename: str = "web_content.txt", task_id: str | None = None) -> HierarchicalResult:
        """Execute the 3-tier pipeline on raw text content with hash check"""
        import time
        start_time = time.time()
        publish = self._make_publisher(task_id)
        
        content_hash = self._calculate_hash(text)
        
        if self.client.check_content_exists(content_hash):
            self.logger.info(f"⏭️ Skipping text ingestion (Hash already exists: {content_hash})")
            publish("skipped", filename=filename, reason="Hash already exists")
            return HierarchicalResult(
                filename=filename,
                status="complete",
                summary_queries=[],
                detail_queries=[],
                conclusion_queries=[],
                committer_result={"merge_notes": "Skipped due to existing hash"},
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        # Prepare tiers from text
        file_size = len(text)
        tiers = {}
        
        summary_size = min(self.summary_chars, int(file_size * 0.1))
        tiers["summary"] = text[:summary_size]
        
        detail_start = int(file_size * 0.1)
        detail_end = int(file_size * 0.9)
        detail_content = text[detail_start:detail_end]
        
        if len(detail_content) > self.detail_chars:
            tiers["detail"] = self.semantic_chunker.split_text(detail_content)
        else:
            tiers["detail"] = detail_content
        
        conclusion_size = min(self.conclusion_chars, int(file_size * 0.1))
        tiers["conclusion"] = text[-conclusion_size:]
        
        # Process tiers
        publish("summary_start", chars=len(tiers["summary"]))
        summary_task = self.process_tier_summary(tiers["summary"])
        detail_chunks = len(tiers["detail"]) if isinstance(tiers["detail"], list) else 1
        publish("detail_start", chunks=detail_chunks)
        detail_task = self.process_tier_detail(tiers["detail"])
        publish("conclusion_start", chars=len(tiers["conclusion"]))
        conclusion_task = self.process_tier_conclusion(tiers["conclusion"])
        
        results = await asyncio.gather(summary_task, detail_task, conclusion_task)
        publish("summary_done", queries=len(results[0].cypher_queries))
        publish("detail_done", queries=len(results[1].cypher_queries))
        publish("conclusion_done", queries=len(results[2].cypher_queries))
        publish("committer_start")
        commit_result = await self.process_committer(results, filename)
        publish("committer_done", final_nodes=len(commit_result.get("final_nodes", [])))
        
        # Intelligence Layer
        publish("enrichment_start")
        web_queries = await self.enrich_with_intelligence(commit_result)
        final_queries = commit_result["final_queries"] + web_queries
        
        # Execute
        # Replace hash placeholders with actual hash
        final_queries = []
        for q in (commit_result["final_queries"] + web_queries):
            final_queries.append(q.replace("HASH_PLACEHOLDER", content_hash))
            
        exec_result = self.execute_to_falkor(final_queries)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        combined_committer_result = {**commit_result, **exec_result}
        status_txt = "complete" if exec_result.get("success", 0) > 0 else "failed"
        publish(
            "pipeline_done" if status_txt == "complete" else "pipeline_failed",
            nodes=exec_result.get("success", 0),
            elapsed_ms=elapsed_ms,
        )

        return HierarchicalResult(
            filename=filename,
            status=status_txt,
            summary_queries=results[0].cypher_queries,
            detail_queries=results[1].cypher_queries,
            conclusion_queries=results[2].cypher_queries,
            committer_result=combined_committer_result,
            processing_time_ms=elapsed_ms,
            total_nodes=exec_result.get("success", sum(r.node_count for r in results)),
            total_edges=exec_result.get("total", sum(r.edge_count for r in results)) - exec_result.get("success", 0)
        )


if __name__ == "__main__":
    ingestor = HierarchicalIngestor()
    ingestor.run()
