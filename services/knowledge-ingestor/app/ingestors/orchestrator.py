"""
Olympus Agentic Ingestor - FULLY AGENTIC VERSION (REFACTORED)
Coordinates the Planner → Knowledge Architect → Committer pipeline using OpenRouter API
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from app.base_ingestor import BaseIngestor
from app.core.llm_utils import LLMUtils
from app.core.models import IngestionResult

logger = logging.getLogger("OlympusOrchestrator")

# Agent system prompts (Optimized with JSON Schema & CoT)
PLANNER_PROMPT = """You are THE PLANNER for Project Olympus.

Your role: Analyze incoming files and determine the optimal ingestion strategy.

Output format (Valid JSON only):
{
  "reasoning": "Brief explanation of your classification",
  "file_type": "markdown|pdf|json|csv|api|web",
  "category": "macro|research|news|price|strategy|event",
  "tools_needed": ["tool1", "tool2"],
  "priority": "high|medium|low",
  "extraction_hint": "Focus area for the Architect"
}"""

ARCHITECT_PROMPT = """You are THE KNOWLEDGE ARCHITECT for Project Olympus - Expert Cypher Graph Builder.

Your mission: Extract entities and complex relationships into valid Cypher queries.

OLYMPUS ONTOLOGY:
- Nodes: Paper, Asset, Concept, MacroIndicator, Event, Strategy, Organization, Country, Person
- Edges: MENTIONS, INFLUENCES, SUPPORTS, CONTRADICTS, TRIGGERS, CORRELATES_WITH, PROPOSES_STRATEGY, IDENTIFIED_IN, AFFECTS, LEADS_TO

MANDATORY RULES:
1. Extract ALL organizations, indicators, and assets.
2. Use PascalCase for Labels, camelCase for properties, UPPERCASE for Relationships.
3. Every node MUST have a 'name' (or 'title' for Paper) and at least one context property (e.g., 'type', 'source', 'value').

Output format (Valid JSON only):
{
  "thought_process": "Explanation of the relationships identified",
  "cypher_queries": [
    "MERGE (a:Asset {name: 'XAUUSD', type: 'COMMODITY'})",
    "MERGE (o:Organization {name: 'Federal Reserve', type: 'CENTRAL_BANK'})",
    "MATCH (o:Organization {name: 'Federal Reserve'}), (a:Asset {name: 'XAUUSD'}) CREATE (o)-[:INFLUENCES {impact: 'high'}]->(a)"
  ]
}"""


class OlympusOrchestrator(BaseIngestor):
    """Main orchestrator for fully agentic ingestion pipeline"""
    
    def __init__(self):
        super().__init__("OlympusOrchestrator")
        
    def read_file(self, path: Path, max_chars: int = 80000) -> Dict[str, Any]:
        """Read file content with intelligent chunking for large files"""
        content = ""
        chunk_info = None
        
        if path.suffix == '.md' or path.suffix == '.txt':
            with open(path, 'r', encoding='utf-8') as f:
                full_content = f.read()
                
            if len(full_content) > max_chars:
                head_size = int(max_chars * 0.3)
                tail_size = max_chars - head_size
                content = full_content[:head_size] + "\n\n... [truncated middle section] ...\n\n" + full_content[-tail_size:]
                chunk_info = {"truncated": True, "original_size": len(full_content), "loaded_size": len(content)}
                logger.info(f"📄 Chunked {path.name}: {len(full_content)} → {len(content)} chars")
            else:
                content = full_content
                
        elif path.suffix == '.json':
            with open(path, 'r', encoding='utf-8') as f:
                content = json.dumps(json.load(f), indent=2)
            if len(content) > max_chars:
                content = content[:max_chars] + "\n... [truncated] ..."
                chunk_info = {"truncated": True, "original_size": len(content), "loaded_size": max_chars}
                
        elif path.suffix == '.pdf':
            content = "[PDF - requires pdf tool]"
        elif path.suffix == '.csv':
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            if len(content) > max_chars:
                lines = content.split('\n')
                header = lines[0] if lines else ""
                remaining = max_chars - len(header) - 50
                kept_lines = []
                for line in lines[1:]:
                    if len('\n'.join(kept_lines)) + len(line) < remaining:
                        kept_lines.append(line)
                content = header + '\n' + '\n'.join(kept_lines) + f"\n... [truncated {len(lines) - len(kept_lines)} rows] ..."
                chunk_info = {"truncated": True, "type": "csv", "original_rows": len(lines)}
        
        return {
            "filename": path.name,
            "path": str(path),
            "extension": path.suffix,
            "content": content,
            "size_bytes": path.stat().st_size,
            "chunk_info": chunk_info
        }
    
    async def run_pipeline(self, file_path: Path) -> IngestionResult:
        """Run the FULL AGENTIC pipeline"""
        import time
        start_time = time.time()
        self.logger.info(f"🚀 Starting AGENTIC pipeline for {file_path.name}")
        
        # Step 1: Read file
        file_data = self.read_file(file_path)
        
        # Step 2: PLANNER Agent
        chunk_note = ""
        if file_data.get('chunk_info'):
            ci = file_data['chunk_info']
            chunk_note = f"\n[Note: File was truncated. Original: {ci.get('original_size', 'N/A')} chars → Loaded: {ci.get('loaded_size', 'N/A')} chars]"
        
        planner_input = f"Filename: {file_data['filename']}\nExtension: {file_data['extension']}\nFile Size: {file_data['size_bytes']} bytes{chunk_note}\n\nContent Preview:\n{file_data['content'][:3000]}"
        planner_result = await LLMUtils.call_llm(PLANNER_PROMPT, planner_input, tier="planner")
        
        if "error" in planner_result:
            return IngestionResult(filename=file_path.name, status="failed", error=planner_result["error"])
        
        # Step 3: KNOWLEDGE ARCHITECT Agent
        architect_input = f"""File: {file_data['filename']}
Category: {planner_result.get('category', 'unknown')}
Priority: {planner_result.get('priority', 'medium')}

Content:
{file_data['content']}"""
        architect_result = await LLMUtils.call_llm(ARCHITECT_PROMPT, architect_input, tier="architect", max_tokens=8000)
        
        if "error" in architect_result:
            return IngestionResult(filename=file_path.name, status="failed", error=architect_result["error"], planner_result=planner_result)
        
        # Step 4: COMMITTER (Execute)
        cypher_queries = architect_result.get("cypher_queries", [])
        committer_result = {}
        
        if cypher_queries:
            committer_result = self.execute_to_falkor(cypher_queries)
        else:
            committer_result = {"error": "No cypher queries generated"}
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        status = "complete" if committer_result.get("success", 0) > 0 else "failed"
        
        return IngestionResult(
            filename=file_path.name,
            status=status,
            planner_result=planner_result,
            architect_result=architect_result,
            committer_result=committer_result,
            processing_time_ms=elapsed_ms,
            total_nodes=committer_result.get("success", 0) # Approximation
        )

    async def run_pipeline_on_text(self, text: str, filename: str = "web_content.txt") -> IngestionResult:
        """Run the FULL AGENTIC pipeline on raw text content"""
        import time
        start_time = time.time()
        self.logger.info(f"🚀 Starting AGENTIC raw text pipeline for {filename}")
        
        file_data = {
            "filename": filename,
            "extension": ".txt",
            "content": text[:80000], # Cap size
            "size_bytes": len(text)
        }
        
        # PLANNER
        planner_input = f"Filename: {filename}\nContent Preview:\n{text[:3000]}"
        planner_result = await LLMUtils.call_llm(PLANNER_PROMPT, planner_input, tier="planner")
        
        if "error" in planner_result:
            return IngestionResult(filename=filename, status="failed", error=planner_result["error"])
        
        # ARCHITECT
        architect_input = f"File: {filename}\nCategory: {planner_result.get('category', 'unknown')}\n\nContent:\n{file_data['content']}"
        architect_result = await LLMUtils.call_llm(ARCHITECT_PROMPT, architect_input, tier="architect", max_tokens=8000)
        
        if "error" in architect_result:
            return IngestionResult(filename=filename, status="failed", error=architect_result["error"], planner_result=planner_result)
        
        # COMMITTER
        cypher_queries = architect_result.get("cypher_queries", [])
        if cypher_queries:
            committer_result = self.execute_to_falkor(cypher_queries)
        else:
            committer_result = {"error": "No cypher queries generated"}
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        status = "complete" if committer_result.get("success", 0) > 0 else "failed"
        
        return IngestionResult(
            filename=filename,
            status=status,
            planner_result=planner_result,
            architect_result=architect_result,
            committer_result=committer_result,
            processing_time_ms=elapsed_ms,
            total_nodes=committer_result.get("success", 0)
        )


if __name__ == "__main__":
    orchestrator = OlympusOrchestrator()
    orchestrator.run()
