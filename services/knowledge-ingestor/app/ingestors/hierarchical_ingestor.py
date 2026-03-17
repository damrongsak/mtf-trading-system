"""
Olympus Ingestor - Hierarchical 3-Tier Processing (REFACTORED)
Professional large file ingestion for financial news & analysis
"""

import json
import logging
import re
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from app.base_ingestor import BaseIngestor
from app.core.llm_utils import LLMUtils
from app.core.logger import get_logger
from app.tools.market_reader import MarketReaderTool
from app.tools.web_search import WebSearchTool
from app.core.models import ChunkResult, HierarchicalResult

logger = get_logger("HierarchicalIngestor")

# ============================================================================
# PROMPT TEMPLATES (Optimized with JSON Schema & CoT)
# ============================================================================

TIER_SUMMARY_PROMPT = """You are THE EXECUTIVE SUMMARY EXPERT for Project Olympus.

Your mission: Extract key metadata and high-level context from the document's introduction.

Output format (Valid JSON only):
{
  "reasoning": "Brief analysis of the introduction",
  "headlines": ["Lead headline", "Secondary event"],
  "tickers": ["XAUUSD", "BTC"],
  "sentiment": "bullish|bearish|neutral",
  "key_numbers": {"label": value},
  "source": "Source name",
  "timestamp": "YYYY-MM-DD",
  "cypher_queries": [
    "MERGE (p:Paper {title: 'Doc Title', source: 'Source', date: 'Date', hash: 'HASH_PLACEHOLDER'})",
    "MERGE (a:Asset {name: 'XAUUSD', type: 'COMMODITY'})"
  ]
}"""


TIER_DETAIL_PROMPT = """You are THE KNOWLEDGE ARCHITECT for Project Olympus.

Your mission: Extract complex entities and relationships into valid Cypher queries based on the MAIN CONTENT.

OLYMPUS ONTOLOGY:
Nodes: Paper, Asset, Concept, MacroIndicator, Event, Strategy, Organization, Country, Person
Edges: MENTIONS, INFLUENCES, SUPPORTS, CONTRADICTS, TRIGGERS, CORRELATES_WITH, PROPOSES_STRATEGY, AFFECTS, LEADS_TO

Output format (Valid JSON only):
{
  "thought_process": "Explanation of identified entities and their links",
  "nodes": [{"label": "Organization", "name": "Fed", "type": "CENTRAL_BANK"}],
  "edges": [{"from": "Fed", "to": "Interest Rates", "type": "AFFECTS"}],
  "cypher_queries": [
    "MERGE (o:Organization {name: 'Federal Reserve', type: 'CENTRAL_BANK'})",
    "MERGE (m:MacroIndicator {name: 'Interest Rates', unit: 'percent'})",
    "MATCH (o:Organization {name: 'Federal Reserve'}), (m:MacroIndicator {name: 'Interest Rates'}) CREATE (o)-[:AFFECTS]->(m)"
  ]
}"""


TIER_CONCLUSION_PROMPT = """You are THE MARKET STRATEGIST for Project Olympus.

Your mission: Extract forward-looking predictions and actionable trading strategies.

Output format (Valid JSON only):
{
  "strategy_logic": "Analysis of why these strategies are proposed",
  "predictions": [{"event": "Gold $3k", "probability": "HIGH", "timeline": "Q2 2026"}],
  "strategies": [{"name": "Long Gold", "timeframe": "H4", "entry": 2850}],
  "risk_factors": ["inflation", "geopolitics"],
  "cypher_queries": [
    "MERGE (s:Strategy {name: 'Long Gold', timeframe: 'H4'})",
    "MERGE (e:Event {name: 'Gold $3k Target', probability: 'HIGH'})",
    "MATCH (s:Strategy {name: 'Long Gold'}), (e:Event {name: 'Gold $3k Target'}) CREATE (s)-[:PROPOSES_STRATEGY]->(e)"
  ]
}"""


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
        
        # Tier sizes
        self.summary_chars = 2000      # First 2KB for summary
        self.detail_chars = 60_000     # 60KB for details (with chunking)
        self.conclusion_chars = 3000    # Last 3KB for conclusion
    
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
            chunks = self._chunk_by_headings(detail_content)
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

    def _chunk_by_headings(self, content: str) -> List[str]:
        """Split content by markdown headings for better context"""
        parts = re.split(r'(?=^##\s+.+$)', content, flags=re.MULTILINE)
        chunks = []
        current = ""
        for part in parts:
            if len(current) + len(part) < 15000:
                current += part
            else:
                if current.strip():
                    chunks.append(current)
                current = part
        if current.strip():
            chunks.append(current)
        return chunks if chunks else [content]
    
    async def process_tier_summary(self, content: str) -> ChunkResult:
        """Tier 1: Executive Summary"""
        result = await LLMUtils.call_llm(TIER_SUMMARY_PROMPT, content, "summary", max_tokens=2000)
        queries = result.get("cypher_queries", [])
        return ChunkResult(
            tier="summary",
            cypher_queries=queries,
            node_count=len(result.get("tickers", [])) + len(result.get("key_numbers", {})),
            edge_count=len(queries),
            raw_response=str(result)[:500]
        )
    
    async def process_tier_detail(self, content: str | List[str]) -> ChunkResult:
        """Tier 2: Full Content Details"""
        if isinstance(content, list):
            all_queries = []
            node_count = 0
            edge_count = 0
            for i, chunk in enumerate(content):
                result = await LLMUtils.call_llm(TIER_DETAIL_PROMPT, chunk, "detail", max_tokens=8000)
                all_queries.extend(result.get("cypher_queries", []))
                node_count += len(result.get("nodes", []))
                edge_count += len(result.get("edges", []))
            cypher_queries = all_queries
        else:
            result = await LLMUtils.call_llm(TIER_DETAIL_PROMPT, content, "detail", max_tokens=8000)
            cypher_queries = result.get("cypher_queries", [])
            node_count = len(result.get("nodes", []))
            edge_count = len(result.get("edges", []))
        
        return ChunkResult(tier="detail", cypher_queries=cypher_queries, node_count=node_count, edge_count=edge_count)
    
    async def process_tier_conclusion(self, content: str) -> ChunkResult:
        """Tier 3: Conclusion & Predictions"""
        result = await LLMUtils.call_llm(TIER_CONCLUSION_PROMPT, content, "conclusion", max_tokens=3000)
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

    async def run_pipeline(self, file_path: Path) -> HierarchicalResult:
        """Execute the full 3-tier pipeline with incremental sync check"""
        import time
        start_time = time.time()
        
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
            return HierarchicalResult(
                filename=file_path.name,
                status="complete",
                summary_queries=[],
                detail_queries=[],
                conclusion_queries=[],
                committer_result={"merge_notes": "Skipped due to existing hash"},
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

        file_data = self.read_file_tiers(file_path)
        
        summary_task = self.process_tier_summary(file_data["tiers"]["summary"])
        detail_task = self.process_tier_detail(file_data["tiers"]["detail"])
        conclusion_task = self.process_tier_conclusion(file_data["tiers"]["conclusion"])
        
        results = await asyncio.gather(summary_task, detail_task, conclusion_task)
        commit_result = await self.process_committer(results, file_path.name)
        
        # --- NEW: Intelligence Layer (Market + Web) ---
        web_queries = await self.enrich_with_intelligence(commit_result)
        final_queries = commit_result["final_queries"] + web_queries
        
        # Execute to FalkorDB
        # Replace hash placeholders with actual hash
        final_queries = []
        for q in (commit_result["final_queries"] + web_queries):
            final_queries.append(q.replace("HASH_PLACEHOLDER", content_hash))
            
        exec_result = self.execute_to_falkor(final_queries)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return HierarchicalResult(
            filename=file_path.name,
            status="complete" if exec_result.get("success", 0) > 0 else "failed",
            summary_queries=results[0].cypher_queries,
            detail_queries=results[1].cypher_queries,
            conclusion_queries=results[2].cypher_queries,
            committer_result=commit_result,
            processing_time_ms=elapsed_ms,
            total_nodes=sum(r.node_count for r in results),
            total_edges=sum(r.edge_count for r in results)
        )

    async def run_pipeline_on_text(self, text: str, filename: str = "web_content.txt") -> HierarchicalResult:
        """Execute the 3-tier pipeline on raw text content with hash check"""
        import time
        start_time = time.time()
        
        content_hash = self._calculate_hash(text)
        
        if self.client.check_content_exists(content_hash):
            self.logger.info(f"⏭️ Skipping text ingestion (Hash already exists: {content_hash})")
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
            tiers["detail"] = self._chunk_by_headings(detail_content)
        else:
            tiers["detail"] = detail_content
        
        conclusion_size = min(self.conclusion_chars, int(file_size * 0.1))
        tiers["conclusion"] = text[-conclusion_size:]
        
        # Process tiers
        summary_task = self.process_tier_summary(tiers["summary"])
        detail_task = self.process_tier_detail(tiers["detail"])
        conclusion_task = self.process_tier_conclusion(tiers["conclusion"])
        
        results = await asyncio.gather(summary_task, detail_task, conclusion_task)
        commit_result = await self.process_committer(results, filename)
        
        # Intelligence Layer
        web_queries = await self.enrich_with_intelligence(commit_result)
        final_queries = commit_result["final_queries"] + web_queries
        
        # Execute
        # Replace hash placeholders with actual hash
        final_queries = []
        for q in (commit_result["final_queries"] + web_queries):
            final_queries.append(q.replace("HASH_PLACEHOLDER", content_hash))
            
        exec_result = self.execute_to_falkor(final_queries)
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        return HierarchicalResult(
            filename=filename,
            status="complete" if exec_result.get("success", 0) > 0 else "failed",
            summary_queries=results[0].cypher_queries,
            detail_queries=results[1].cypher_queries,
            conclusion_queries=results[2].cypher_queries,
            committer_result=commit_result,
            processing_time_ms=elapsed_ms,
            total_nodes=sum(r.node_count for r in results),
            total_edges=sum(r.edge_count for r in results)
        )


if __name__ == "__main__":
    ingestor = HierarchicalIngestor()
    ingestor.run()
