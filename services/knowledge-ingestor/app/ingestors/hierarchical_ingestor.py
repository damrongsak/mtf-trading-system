"""
Olympus Ingestor - Hierarchical 3-Tier Processing (REFACTORED)
Professional large file ingestion for financial news & analysis
"""

import json
import asyncio
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.base_ingestor import BaseIngestor
from app.core.llm_utils import LLMUtils
from app.core.logging_config import get_logger
from app.core.semantic_chunker import SemanticChunker
from app.core.ontology import GraphExtractionSchema
from app.core.doc_analyzer import DocumentAnalyzer, DocStructure
from app.tools.market_reader import MarketReaderTool
from app.tools.web_search import WebSearchTool
from app.core.app_config import config
from app.core.models import ChunkResult, HierarchicalResult
from app.core.orchestrator import orchestrator

logger = get_logger("HierarchicalIngestor")

# ============================================================================
# PROMPT TEMPLATES (Optimized with JSON Schema & CoT)
# ============================================================================

# ============================================================================
# PROMPT TEMPLATES (Aligned with Olympus Gold Standard)
# ============================================================================

TIER_SUMMARY_PROMPT = """You are THE EXECUTIVE SUMMARY EXPERT for Project Olympus.

GLOBAL CONTEXT:
Document Title: {doc_title}
Key Themes: {main_themes}
Anchor Entities: {key_entities}

Your mission: Extract key metadata and high-level context.
Return JSON ONLY with this schema:
{{
  "source": {{
    "title": "{doc_title}",
    "author": "Identify author if present",
    "thesis": "Core thesis",
    "tickers": ["GLD", "SPY"],
    "indicators": ["USCPI", "FEDFUNDS"]
  }}
}}
Note: Map generic terms to Tickers where possible (e.g. 'Gold' -> 'XAUUSD').
"""


TIER_DETAIL_PROMPT = """You are THE KNOWLEDGE ARCHITECT for Project Olympus.

GLOBAL CONTEXT:
Document Title: {doc_title}
Key Themes: {main_themes}
Anchor Entities: {key_entities}

Your mission: Extract structured concepts, Smart Money Patterns (SMC), and causal relationships from the provided text chunk.

STRICT EXTRACTION POLICY:
- EXHAUSTIVE: Do NOT summarize. Extract EVERY unique trading term, pattern, and technical concept mentioned.
- LABEL PRECISION: 
    - Put TRADING PATTERNS (Order Blocks, FVG, BOS, Liquidity Sweeps, Judas Swing, Volume Gaps) into 'smc_patterns'.
    - Put GENERAL CONCEPTS (Inflation, Liquidity as a general term, Interest Rates, etc.) into 'concepts'.
- DENSITY: High knowledge density is required. If a sentence contains a technical term (e.g., 'Judas Swing', 'BOS'), it MUST be a node.

JSON SCHEMA REQUIREMENT:
{{
  "concepts": [
    {{
      "name": "Concept Name",
      "definition": "Strict academic definition",
      "math": "Latex formula if applicable",
      "example": "Practical trading example",
      "prerequisites": ["Existing Concept Names"],
      "influences": [
        {{"target": "Target Concept", "direction": "positive|negative", "strength": 1-5, "context": "Detailed reasoning"}}
      ]
    }}
  ],
  "smc_patterns": [
    {{
      "name": "Pattern Name (e.g. Order Block)",
      "definition": "How to identify it",
      "logic": "The institutional logic behind it",
      "timeframe": "Relevant timeframe if mentioned"
    }}
  ]
}}
"""


TIER_CONCLUSION_PROMPT = """You are THE MARKET STRATEGIST for Project Olympus.

Your mission: Extract forward-looking predictions and actionable trading strategies.

Output format (Valid JSON only):
{{
  "strategy_logic": "Analysis of why these strategies are proposed",
  "predictions": [{{ "event": "Gold $3k", "probability": "HIGH", "timeline": "Q2 2026" }}],
  "strategies": [{{ "name": "Long Gold", "timeframe": "H4", "entry": 2850 }}]
}}"""


COMMITTER_PROMPT = """You are THE COMMITTER for Project Olympus.

Your role: Merge results from 3 tiers (Summary, Detail, Conclusion) into a single unified JSON object.
Deduplicate entities and resolve conflicts. Ensure EVERY minor pattern found in detail tier is preserved.

STRICT SCHEMATIC ENFORCEMENT:
- All Smart Money Patterns (e.g. Order Block, FVG, BOS, Liquidity, Judas Swing) MUST be placed in the 'smc_patterns' list.
- Standard macroeconomic or non-trading institutional concepts go in 'concepts'. 
- DO NOT BLEND THEM. If it's a tradeable pattern, it's an 'smc_pattern'.

Output format (Valid JSON only):
{{
  "source": {{
    "title": "...",
    "author": "...",
    "thesis": "...",
    "tickers": [],
    "indicators": []
  }},
  "concepts": [
    {{
      "name": "...",
      "definition": "...",
      "math": "...",
      "example": "...",
      "prerequisites": [],
      "influences": [
        {{"target": "...", "direction": "...", "strength": 5, "context": "..."}}
      ]
    }}
  ],
  "smc_patterns": [
    {{
      "name": "...",
      "definition": "...",
      "logic": "...",
      "timeframe": "..."
    }}
  ]
}}"""


WEBSCOUT_PROMPT = """You are THE WEBSCOUT for Project Olympus.

Your mission: Given the extracted entities and merge notes, generate 1-3 highly targeted search queries to find real-time context or missing facts (especially specific trading rules, institutional behaviors, or asset correlations) that enrich the Knowledge Graph.

Input:
{scout_input}

Output format (Valid JSON only):
{{
  "search_required": true|false,
  "queries": ["Specific search query 1", "Specific search query 2"],
  "reasoning": "Why these queries are needed"
}}"""

AUDITOR_PROMPT = """You are THE KNOWLEDGE AUDITOR for Project Olympus.

Your mission: Review the extracted Knowledge Graph triplets and identify any semantic errors, hallucinations, or logical inconsistencies.

ONTOLOGY RULES:
- Nodes must fit categories: Asset, Concept, MacroIndicator, Event, Strategy, Organization, Country, Person, SMC_Pattern, Timeframe.
- Relationships must make logical sense (e.g., an Asset cannot 'PROPOSE' a Strategy, but a Person or Strategy can).
- Deduplicate names (e.g., 'Fed' and 'Federal Reserve' should be the same).

Output format (Valid JSON only):
{
  "is_valid": true|false,
  "corrections": [
    {"type": "RENAME", "old": "...", "new": "..."},
    {"type": "DELETE_RELATIONSHIP", "from": "...", "to": "...", "reason": "..."},
    {"type": "MERGE_NODES", "nodes": ["A", "B"], "canonical": "A"}
  ],
  "reasoning": "Explain your audit decisions"
}"""


class HierarchicalIngestor(BaseIngestor):
    """3-Tier Hierarchical Ingestion for Large Financial Documents"""

    def __init__(self):
        super().__init__("OlympusHierarchicalIngestor")
        self.summary_chars = 2000
        self.detail_chars = 60_000
        self.conclusion_chars = 3000
        self.semantic_chunker = SemanticChunker(chunk_size=12000, chunk_overlap=1000)

    async def update_stage(
        self,
        task_id: str | None,
        stage: str,
        detail: Optional[str] = None,
        percentage: float = 0.0,
    ):
        """Update task progress via orchestrator if task_id exists."""
        if task_id:
            await orchestrator.update_progress(
                task_id, stage=stage, detail=detail, percentage=percentage
            )
        self.logger.info(f"📍 Stage: {stage} | {detail or ''}")

    def read_file_tiers(self, path: Path) -> Dict[str, Any]:
        """Read file and split into 3 tiers (supports PDF and text)"""
        if path.suffix.lower() == ".pdf":
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
            with open(path, "r", encoding="utf-8") as f:
                full_content = f.read()

        file_size = len(full_content)
        tiers: Dict[str, Any] = {}
        metadata: Dict[str, Any] = {"filename": path.name, "original_size": file_size, "tier_sizes": {}}

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
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def process_tier_summary(
        self, content: str, doc_analysis: DocStructure
    ) -> Dict[str, Any]:
        """Tier 1: Executive Summary with Structural Context"""
        prompt = TIER_SUMMARY_PROMPT.format(
            doc_title=doc_analysis.title,
            main_themes=", ".join(doc_analysis.main_themes),
            key_entities=", ".join(doc_analysis.key_entities),
        )
        result = await LLMUtils.call_llm(prompt, content, "summary", max_tokens=2000)
        return result

    async def process_tier_detail(
        self, content: str | List[str], doc_analysis: DocStructure
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Tier 2: Full Content Details with Structured Schema Enforcement"""
        all_results = {"concepts": [], "smc_patterns": []}
        prompt = TIER_DETAIL_PROMPT.format(
            doc_title=doc_analysis.title,
            main_themes=", ".join(doc_analysis.main_themes),
            key_entities=", ".join(doc_analysis.key_entities),
        )

        chunks = content if isinstance(content, list) else [content]
        for i, chunk in enumerate(chunks):
            try:
                result = await LLMUtils.call_llm(prompt, chunk, f"detail_{i}", max_tokens=4000)
                if "concepts" in result:
                    all_results["concepts"].extend(result["concepts"])
                if "smc_patterns" in result:
                    all_results["smc_patterns"].extend(result["smc_patterns"])
            except Exception as e:
                self.logger.error(f"❌ Detail Ingestion failed for chunk {i}: {e}")
        
        return all_results

    async def process_tier_conclusion(
        self, content: str, doc_analysis: DocStructure
    ) -> Dict[str, Any]:
        """Tier 3: Conclusion & Predictions with Structural Context"""
        prompt = TIER_CONCLUSION_PROMPT.format(
            doc_title=doc_analysis.title,
            main_themes=", ".join(doc_analysis.main_themes),
            key_entities=", ".join(doc_analysis.key_entities),
        )
        result = await LLMUtils.call_llm(prompt, content, "conclusion", max_tokens=3000)
        return result

    async def process_committer(
        self, results: List[Any], filename: str
    ) -> Dict[str, Any]:
        """Merge all tiers into a single source-controlled knowledge object"""
        detail_results = results[1] # Now a dict with concepts and smc_patterns
        merge_input = f"""Filename: {filename}
Summary Tier: {json.dumps(results[0])}
Detail Concepts: {json.dumps(detail_results.get("concepts", []))}
Detail SMC Patterns: {json.dumps(detail_results.get("smc_patterns", []))}
Conclusion Tier: {json.dumps(results[2])}
"""
        result = await LLMUtils.call_llm(
            COMMITTER_PROMPT, merge_input, tier="committer", max_tokens=4000
        )
        return result

    def json_to_cypher(self, data: Dict[str, Any], content_hash: str, filename: str) -> List[str]:
        """Translate the Olympus Gold Standard JSON into Cypher queries (Ref: olympus_falkor_ingestor.py)"""
        source = data.get("source", {})
        concepts = data.get("concepts", [])
        smc_patterns = data.get("smc_patterns", [])
        
        self.logger.info(f"📐 [Cypher] Translating results for {filename}: {len(concepts)} concepts, {len(smc_patterns)} smc_patterns")
        
        queries = []

        # 1. Source Node
        source_name = str(source.get("title") or filename).replace('"', "'")
        source_thesis = str(source.get("thesis") or "").replace('"', "'")
        source_author = str(source.get("author") or "Unknown").replace('"', "'")
        
        queries.append(
            f'MERGE (s:Source {{name: "{source_name}"}}) '
            f'SET s.author = "{source_author}", s.thesis = "{source_thesis}", '
            f's.hash = "{content_hash}", s.date = "{datetime.now().strftime("%Y-%m-%d")}", '
            f's.file_ref = "{filename}"'
        )
        
        for t in source.get("tickers", []):
            tick_id = str(t).replace('"', "'")
            queries.append(f'MERGE (tick:Ticker {{name: "{tick_id}"}}) MERGE (s)-[:COVERS]->(tick)')
        for ind in source.get("indicators", []):
            ind_id = str(ind).replace('"', "'")
            queries.append(f'MERGE (i:Indicator {{name: "{ind_id}"}}) MERGE (s)-[:COVERS]->(i)')

        # 2. Concept Nodes
        for c in concepts:
            name = str(c.get("name") or "Unnamed Concept").replace('"', "'")
            definition = str(c.get("definition") or "").replace('"', "'")
            math = str(c.get("math") or "").replace('"', "'")
            example = str(c.get("example") or "").replace('"', "'")
            
            queries.append(f'MERGE (c:Concept {{name: "{name}"}}) SET c.definition = "{definition}", c.math = "{math}", c.example = "{example}"')
            queries.append(f'MATCH (s:Source {{name: "{source_name}"}}), (c:Concept {{name: "{name}"}}) MERGE (s)-[:MENTIONS]->(c)')

            # Prerequisites
            for pr in c.get("prerequisites", []):
                pr_name = str(pr).replace('"', "'")
                queries.append(f'MERGE (:Concept {{name: "{pr_name}"}})')
                queries.append(f'MATCH (c:Concept {{name: "{name}"}}), (p:Concept {{name: "{pr_name}"}}) MERGE (c)-[:PREREQUISITE]->(p)')
            
            # Influences
            for inf in c.get("influences", []):
                if isinstance(inf, dict) and "target" in inf:
                    target = str(inf.get("target") or "Unknown").replace('"', "'")
                    queries.append(f'MERGE (t:Concept {{name: "{target}"}})')
                    
                    inf_direction = str(inf.get("direction", "positive")).replace('"', "'")
                    inf_strength = inf.get("strength", 3)
                    inf_context = str(inf.get("context") or "").replace('"', "'")
                    
                    queries.append(
                        f'MATCH (c:Concept {{name: "{name}"}}), (t:Concept {{name: "{target}"}}) '
                        f'MERGE (c)-[r:INFLUENCES]->(t) '
                        f'SET r.direction = "{inf_direction}", r.strength = {inf_strength}, r.context = "{inf_context}"'
                    )

        # 3. SMC Pattern Nodes
        for p in smc_patterns:
            name = str(p.get("name") or "Unnamed Pattern").replace('"', "'")
            definition = str(p.get("definition") or "").replace('"', "'")
            logic = str(p.get("logic") or "").replace('"', "'")
            timeframe = str(p.get("timeframe") or "").replace('"', "'")

            queries.append(f'MERGE (pc:SMC_Pattern {{name: "{name}"}}) SET pc.definition = "{definition}", pc.logic = "{logic}", pc.timeframe = "{timeframe}"')
            queries.append(f'MATCH (s:Source {{name: "{source_name}"}}), (pc:SMC_Pattern {{name: "{name}"}}) MERGE (s)-[:MENTIONS]->(pc)')

        return queries

    async def enrich_with_intelligence(
        self, committer_result: Dict[str, Any]
    ) -> List[str]:
        # --- Part 1: Real-Time Market Discovery (Phase 7) ---
        enrichment_queries = []
        assets_to_check = {
            "Gold": ["Gold", "XAU", "XAUUSD"],
            "Bitcoin": ["Bitcoin", "BTC", "BTCUSD"],
            "Silver": ["Silver", "XAG", "XAGUSD"],
        }
        combined_nodes = [n.lower() for n in committer_result.get("final_nodes", [])]

        for asset_canonical, aliases in assets_to_check.items():
            if any(alias.lower() in combined_nodes for alias in aliases):
                try:
                    # ✅ FIX: MarketReaderTool.get_spot_price IS ALREADY ASYNC. Await it directly.
                    price = await asyncio.wait_for(
                        MarketReaderTool.get_spot_price(asset_canonical),
                        timeout=config.ki_tool_timeout,
                    )
                    if price:
                        self.logger.info(
                            f"✨ Market Enrichment: {asset_canonical} -> ${price}"
                        )
                        now_str = datetime.now().isoformat()
                        enrichment_queries.append(f"""
                            MERGE (a:Asset {{name: '{asset_canonical}'}})
                            SET a.real_time_price = {price}, a.last_market_sync = '{now_str}', a.status = 'ENRICHED'
                        """)
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"⏱️ Market enrichment timed out for {asset_canonical}"
                    )

        # --- Part 2: WebScout Event Discovery (Phase 11) ---
        scout_input = f"Extracted Nodes: {committer_result.get('final_nodes')}\nMerge Notes: {committer_result.get('merge_notes')}"
        scout_report = await LLMUtils.call_llm(
            WEBSCOUT_PROMPT, scout_input, tier="web_scout", max_tokens=1000
        )

        if scout_report.get("search_required") and scout_report.get("queries"):
            for query in scout_report["queries"]:
                self.logger.info(f"🕵️ WebScout investigating: '{query}'")
                try:
                    live_data = await asyncio.wait_for(
                        WebSearchTool.search_and_summarize(query),
                        timeout=config.ki_tool_timeout,
                    )
                    safe_data = live_data.replace("'", "\\'").replace("\n", "\\n")
                    now_str = datetime.now().isoformat()

                    enrichment_queries.append(f"""
                        MERGE (w:WebIntelligence {{query: '{query.replace("'", "\\'")}'}})
                        SET w.content = '{safe_data}', w.last_updated = '{now_str}', w.source = 'DuckDuckGo_Live'
                    """)

                    for node_name in committer_result.get("final_nodes", []):
                        if node_name.lower() in query.lower():
                            enrichment_queries.append(
                                f"MATCH (n), (w:WebIntelligence {{query: '{query.replace("'", "\\'")}'}}) WHERE n.name = '{node_name}' MERGE (n)-[:HAS_LIVE_CONTEXT]->(w)"
                            )
                except asyncio.TimeoutError:
                    self.logger.warning(
                        f"⏱️ WebScout investigation timed out for: {query}"
                    )

        return enrichment_queries

    async def audit_knowledge(
        self, extraction: GraphExtractionSchema
    ) -> GraphExtractionSchema:
        """Phase 2: Use LLM to audit and refine extracted knowledge"""
        nodes_info = [{"label": n.label, "name": n.name} for n in extraction.nodes]
        rels_info = [
            {"from": r.from_node, "to": r.to_node, "type": r.type}
            for r in extraction.relationships
        ]

        input_data = (
            f"Nodes: {json.dumps(nodes_info)}\nRelationships: {json.dumps(rels_info)}"
        )

        try:
            audit_result = await LLMUtils.call_llm(
                AUDITOR_PROMPT, input_data, tier="auditor", max_tokens=2000
            )

            if not audit_result.get("is_valid", True) and "corrections" in audit_result:
                self.logger.info(
                    f"🧹 Auditor found {len(audit_result['corrections'])} potential issues."
                )
                # Basic implementation of corrections (can be expanded)
                for corr in audit_result["corrections"]:
                    if corr["type"] == "RENAME":
                        for n in extraction.nodes:
                            if n.name == corr["old"]:
                                n.name = corr["new"]
                    elif corr["type"] == "DELETE_RELATIONSHIP":
                        extraction.relationships = [
                            r
                            for r in extraction.relationships
                            if not (
                                r.from_node == corr["from"] and r.to_node == corr["to"]
                            )
                        ]

            return extraction
        except Exception as e:
            self.logger.warning(f"⚠️ Audit failed, proceeding with raw extraction: {e}")
            return extraction

    async def run_pipeline(
        self, file_path: Path, task_id: str | None = None, force: bool = False
    ) -> HierarchicalResult:
        """Execute the full 3-tier pipeline (Source -> Concepts -> Cypher)"""
        import time
        import shutil

        start_time = time.time()
        with open(file_path, "r", encoding="utf-8") as f:
            full_content = f.read()

        content_hash = self._calculate_hash(full_content)

        # Check if already exists in FalkorDB (Skip if exists)
        if self.client.check_content_exists(content_hash) and not force:
            await self.update_stage(task_id, "skipped", detail=f"Hash {content_hash} exists")
            return HierarchicalResult(
                filename=file_path.name,
                status="complete",
                summary_queries=[],
                detail_queries=[],
                conclusion_queries=[],
                committer_result={"merge_notes": "Skipped due to existing hash"},
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # 1. Structural Analysis
        await self.update_stage(task_id, "doc_analysis_start", detail="Analyzing structure")
        doc_analysis = await DocumentAnalyzer.analyze(full_content[:15000])
        
        file_data = self.read_file_tiers(file_path)

        # 2. Tiered Processing
        await self.update_stage(task_id, "processing_tiers", detail="Running Summary, Detail, Conclusion tiers")
        summary_res = await self.process_tier_summary(file_data["tiers"]["summary"], doc_analysis)
        detail_res = await self.process_tier_detail(file_data["tiers"]["detail"], doc_analysis)
        conclusion_res = await self.process_tier_conclusion(file_data["tiers"]["conclusion"], doc_analysis)

        # 3. Synthesis (Committer)
        await self.update_stage(task_id, "committer_start", detail="Synthesizing knowledge objects")
        merged_json = await self.process_committer([summary_res, detail_res, conclusion_res], file_path.name)

        # 4. Conversion to Cypher
        await self.update_stage(task_id, "cypher_generation", detail="Translating to Graph Queries")
        final_queries = self.json_to_cypher(merged_json, content_hash, file_path.name)

        # 5. Commit to FalkorDB
        await self.update_stage(task_id, "falkordb_commit", detail=f"Committing {len(final_queries)} queries")
        exec_result = self.execute_to_falkor(final_queries)

        # 6. Archival (Timestamped)
        if exec_result.get("success", 0) > 0 or force:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                archive_name = f"{timestamp}_{file_path.name}"
                archive_dir = file_path.parent / "archive"
                archive_dir.mkdir(exist_ok=True)
                shutil.move(str(file_path), str(archive_dir / archive_name))
                self.logger.info(f"📦 Archived {file_path.name} -> {archive_name}")
            except Exception as e:
                self.logger.warning(f"⚠️ Archival failed (likely read-only FS), skipping: {e}")

        elapsed_ms = int((time.time() - start_time) * 1000)
        return HierarchicalResult(
            filename=file_path.name,
            status="complete" if exec_result.get("success", 0) > 0 else "failed",
            summary_queries=[], # Deprecated in favor of merged JSON flow
            detail_queries=[],
            conclusion_queries=[],
            committer_result=merged_json,
            processing_time_ms=elapsed_ms,
            total_nodes=exec_result.get("success", 0),
            total_edges=exec_result.get("total", 0) - exec_result.get("success", 0),
        )

    async def run_pipeline_on_text(
        self, text: str, filename: str = "web_content.txt", task_id: str | None = None
    ) -> HierarchicalResult:
        """Execute the 3-tier pipeline on raw text content with hash check"""
        import time

        start_time = time.time()
        publish = self._make_publisher(task_id)

        content_hash = self._calculate_hash(text)

        if self.client.check_content_exists(content_hash):
            self.logger.info(
                f"⏭️ Skipping text ingestion (Hash already exists: {content_hash})"
            )
            publish("skipped", filename=filename, reason="Hash already exists")
            return HierarchicalResult(
                filename=filename,
                status="complete",
                summary_queries=[],
                detail_queries=[],
                conclusion_queries=[],
                committer_result={"merge_notes": "Skipped due to existing hash"},
                processing_time_ms=int((time.time() - start_time) * 1000),
            )

        # 1. Structural Analysis
        doc_analysis = await DocumentAnalyzer.analyze(text[:15000])

        # Prepare tiers from text
        file_size = len(text)
        tiers: Dict[str, Any] = {}

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
        summary_task = self.process_tier_summary(tiers["summary"], doc_analysis)
        detail_chunks = len(tiers["detail"]) if isinstance(tiers["detail"], list) else 1
        publish("detail_start", chunks=detail_chunks)
        detail_task = self.process_tier_detail(tiers["detail"], doc_analysis)
        publish("conclusion_start", chars=len(tiers["conclusion"]))
        conclusion_task = self.process_tier_conclusion(tiers["conclusion"], doc_analysis)

        results_gather = await asyncio.gather(summary_task, detail_task, conclusion_task)
        results = list(results_gather)
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
        for q in commit_result["final_queries"] + web_queries:
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
            total_edges=exec_result.get("total", sum(r.edge_count for r in results))
            - exec_result.get("success", 0),
        )


    def _make_publisher(self, task_id: str | None):
        """Helper to publish status updates if task_id exists"""
        def publish(stage: str, **kwargs):
            if task_id:
                # Fire and forget status update
                asyncio.create_task(self.update_stage(task_id, stage, **kwargs))
        return publish


if __name__ == "__main__":
    ingestor = HierarchicalIngestor()
    ingestor.run()
