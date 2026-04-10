from __future__ import annotations
import asyncio
import json
from typing import List, Dict, Any, Optional
from app.core.app_config import config
from app.core.logging_config import get_logger
from app.tools.falkordb_client import FalkorDBClient
from app.core.llm_utils import LLMUtils

logger = get_logger("ConceptMerger")

class ConceptMerger:
    """
    Manual maintenance tool for semantic concept deduplication in FalkorDB.
    Follows the Olympus reference logic for high-density knowledge graphs.
    """

    def __init__(self, graph_name: Optional[str] = None):
        self.client = FalkorDBClient(
            host=config.falkor_host,
            port=config.falkor_port,
            graph_name=graph_name or config.graph_name,
        )
        self.is_connected = False

    def connect(self):
        """Ensure connection to FalkorDB"""
        if not self.is_connected:
            self.client.connect()
            self.is_connected = True

    async def get_all_concepts(self) -> List[str]:
        """Fetch all unique concept names from the graph"""
        self.connect()
        query = "MATCH (c:Concept) RETURN c.name as name"
        try:
            res = await asyncio.to_thread(self.client.execute_query, query)
            if res.get('status') == 'success' and len(res.get('result', [])) > 1:
                # result[0] is headers, result[1] is data
                return [row[0] for row in res['result'][1]]
        except Exception as e:
            logger.error(f"Failed to fetch concepts: {e}")
        return []

    async def find_duplicates_llm(self, concepts: List[str]) -> List[Dict[str, Any]]:
        """Ask LLM to identify groups of identical concepts for merging"""
        if not concepts:
            return []
            
        prompt = f"""
        Analyze the following list of economic and trading concepts.
        Identify groups that refer to the SAME fundamental concept but have different naming conventions.
        (e.g., "Artificial Intelligence" and "Artificial Intelligence (AI)", "Capex" and "Capital Expenditure").
        
        Output a JSON list of objects, each representing a merge group:
        {{
          "merge_groups": [
            {{
              "canonical_name": "The best, most standard name for the concept",
              "duplicates": ["list", "of", "names", "to", "merge", "into", "canonical"]
            }}
          ]
        }}
        
        Only include items that are CERTAINLY the same. If unsure, do not include them.
        
        Concepts to Analyze:
        {json.dumps(concepts, indent=2)}
        """
        
        try:
            logger.info(f"🧠 Asking LLM to analyze {len(concepts)} concepts for duplicates...")
            result = await LLMUtils.call_llm(prompt, "", tier="merger", max_tokens=2000)
            
            # Handle possible varied JSON structures from LLM
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                for key in ["merge_groups", "groups", "clusters"]:
                    if key in result and isinstance(result[key], list):
                        return result[key]
            return []
        except Exception as e:
            logger.error(f"❌ LLM Clustering failed: {e}")
            return []

    async def merge_group(self, group: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Execute the merge for a specific group in FalkorDB"""
        canonical = group["canonical_name"].replace('"', "'")
        duplicates = group["duplicates"]
        
        logger.info(f"🔄 Processing merge group: '{canonical}' ({len(duplicates)} duplicates)")
        
        queries = []
        # 1. Ensure canonical node exists
        queries.append(f'MERGE (:Concept {{name: "{canonical}"}})')
        
        for dup in duplicates:
            dup_clean = dup.replace('"', "'")
            if dup_clean == canonical:
                continue
            
            # 2. Re-point MENTIONS relationships
            queries.append(
                f'MATCH (s:Source)-[r:MENTIONS]->(c:Concept {{name: "{dup_clean}"}}), '
                f'(target:Concept {{name: "{canonical}"}}) '
                f'MERGE (s)-[:MENTIONS]->(target)'
            )
            
            # 3. Move PREREQUISITE relationships (outgoing)
            queries.append(
                f'MATCH (c:Concept {{name: "{dup_clean}"}})-[r:PREREQUISITE]->(p:Concept), '
                f'(target:Concept {{name: "{canonical}"}}) '
                f'MERGE (target)-[:PREREQUISITE]->(p)'
            )
            
            # 4. Move PREREQUISITE relationships (incoming)
            queries.append(
                f'MATCH (p:Concept)-[r:PREREQUISITE]->(c:Concept {{name: "{dup_clean}"}}), '
                f'(target:Concept {{name: "{canonical}"}}) '
                f'MERGE (p)-[:PREREQUISITE]->(target)'
            )
            
            # 5. Aggregate properties (Safe aggregate: set if missing)
            queries.append(
                f"MATCH (c:Concept {{name: '{dup_clean}'}}), (target:Concept {{name: '{canonical}'}}) "
                f"SET target.definition = COALESCE(target.definition, c.definition), "
                f"target.math = COALESCE(target.math, c.math), "
                f"target.example = COALESCE(target.example, c.example)"
            )
            
            # 6. Delete old node (Only if approved by execute)
            if not dry_run:
                queries.append(f'MATCH (c:Concept {{name: "{dup_clean}"}}) DELETE c')

        if dry_run:
            logger.info(f"📝 DRY RUN: Would execute {len(queries)} merge steps for '{canonical}'")
            return {"status": "dry_run", "queries": queries}
        else:
            try:
                self.connect()
                res = await asyncio.to_thread(self.client.execute_batch, queries)
                logger.info(f"✅ Merge successful for '{canonical}': {res.get('success')}/{res.get('total')} queries")
                return {"status": "success", "executed": res.get('success'), "total": res.get('total')}
            except Exception as e:
                logger.error(f"❌ Merge failed for '{canonical}': {e}")
                return {"status": "failed", "error": str(e)}

    async def run_maintenance(self, dry_run: bool = True, batch_size: int = 50) -> Dict[str, Any]:
        """Main entry point for manual maintenance trigger"""
        concepts = await self.get_all_concepts()
        if not concepts:
            return {"status": "no_concepts_found"}
            
        logger.info(f"🔍 Starting maintenance on {len(concepts)} concepts...")
        concepts.sort()
        
        all_results = []
        for i in range(0, len(concepts), batch_size):
            chunk = concepts[i : i + batch_size]
            groups = await self.find_duplicates_llm(chunk)
            
            for group in groups:
                res = await self.merge_group(group, dry_run=dry_run)
                all_results.append({**group, "result": res})
                
        return {
            "status": "completed",
            "dry_run": dry_run,
            "groups_processed": len(all_results),
            "details": all_results
        }
