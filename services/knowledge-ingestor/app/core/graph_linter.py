"""
Graph Linter Utility for Project Olympus.
Responsible for data hygiene, entity resolution, and graph maintenance.
"""

import logging
import asyncio
from typing import List, Dict, Any, Tuple
from app.tools.falkordb_client import FalkorDBClient
from app.core.llm_utils import LLMUtils
from pydantic import BaseModel, Field

logger = logging.getLogger("GraphLinter")

class MergeDecision(BaseModel):
    """LLM decision on whether two nodes should be merged"""
    should_merge: bool = Field(..., description="True if both nodes represent the same entity")
    canonical_name: str = Field(..., description="The preferred name to keep")
    reasoning: str = Field(..., description="Explanation for the decision")

class GraphLinter:
    """Maintains the health and integrity of the Knowledge Graph"""

    def __init__(self):
        self.client = FalkorDBClient()
        self.graph_name = "OlympusKnowledgeGraph"

    async def run_linting_cycle(self) -> Dict[str, Any]:
        """Execute a full maintenance cycle"""
        logger.info("🧹 Starting Periodic Graph Linting Cycle...")
        
        stats = {
            "orphans_removed": 0,
            "nodes_merged": 0,
            "errors": []
        }

        # 1. Remove Orphan Nodes
        stats["orphans_removed"] = await self.cleanup_orphans()

        # 2. Entity Resolution (Fuzzy Merging)
        stats["nodes_merged"] = await self.resolve_entities()

        logger.info(f"✅ Linting Cycle Complete: {stats}")
        return stats

    async def cleanup_orphans(self) -> int:
        """Find and remove nodes with zero relationships"""
        query = "MATCH (n) WHERE degree(n) = 0 DELETE n"
        try:
            result = self.client.execute_query(query)
            # FalkorDB returns nodes_deleted in stats
            deleted = result.get("stats", {}).get("nodes_deleted", 0)
            if deleted > 0:
                logger.info(f"🗑️ Removed {deleted} orphan nodes")
            return deleted
        except Exception as e:
            logger.error(f"Cleanup orphans failed: {e}")
            return 0

    async def resolve_entities(self) -> int:
        """Find similar nodes and merge them using LLM reasoning"""
        merge_count = 0
        labels_to_check = ["Organization", "Asset", "Concept", "Person", "Country"]
        
        for label in labels_to_check:
            nodes = await self._get_all_nodes_by_label(label)
            if len(nodes) < 2:
                continue

            # Simple O(n^2) check for similarity (optimized for small-medium batches)
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    node_a = nodes[i]
                    node_b = nodes[j]
                    
                    if self._is_likely_duplicate(node_a, node_b):
                        decision = await self._ask_llm_to_merge(label, node_a, node_b)
                        if decision.should_merge:
                            await self._merge_nodes(label, node_a, node_b, decision.canonical_name)
                            merge_count += 1
                            # Update local list to prevent re-merging
                            nodes[j] = decision.canonical_name 
        
        return merge_count

    async def _get_all_nodes_by_label(self, label: str) -> List[str]:
        """Fetch all node names for a specific label"""
        query = f"MATCH (n:{label}) RETURN n.name"
        try:
            result = self.client.execute_query(query)
            return [row[0] for row in result.get("results", [])]
        except:
            return []

    def _is_likely_duplicate(self, name_a: str, name_b: str) -> bool:
        """Heuristic check for potential duplicates"""
        a, b = name_a.lower(), name_b.lower()
        if a == b: return True
        # Check if one is a substring of another (e.g., 'Fed' and 'Federal Reserve')
        if len(a) > 2 and len(b) > 2:
            if a in b or b in a: return True
        return False

    async def _ask_llm_to_merge(self, label: str, name_a: str, name_b: str) -> MergeDecision:
        """Use LLM to decide if two nodes are semantically the same"""
        system_prompt = f"You are a Graph Data Specialist for Project Olympus. Decide if these two {label} nodes represent the SAME entity."
        user_prompt = f"Node A: '{name_a}'\nNode B: '{name_b}'\nShould they be merged? If yes, provide the canonical name."
        
        try:
            return await LLMUtils.call_llm_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=MergeDecision,
                tier="linter_decision"
            )
        except:
            return MergeDecision(should_merge=False, canonical_name=name_a, reasoning="LLM failed")

    async def _merge_nodes(self, label: str, name_a: str, name_b: str, canonical_name: str):
        """Execute Cypher commands to merge relationships and delete duplicate"""
        logger.info(f"🔄 Merging '{name_a}' and '{name_b}' -> '{canonical_name}'")
        
        # 1. Create the canonical node if it doesn't exist
        # 2. Redirect all relationships from old nodes to canonical
        # 3. Delete old nodes
        
        # Simplified FalkorDB Merge Pattern
        queries = [
            f"MATCH (old {{name: '{name_a}'}}), (canonical {{name: '{canonical_name}'}}) "
            f"WHERE id(old) <> id(canonical) "
            f"MATCH (old)-[r]->(other) MERGE (canonical)-[new_r:TYPE(r)]->(other) SET new_r = properties(r)",
            
            f"MATCH (old {{name: '{name_a}'}}), (canonical {{name: '{canonical_name}'}}) "
            f"WHERE id(old) <> id(canonical) "
            f"MATCH (other)-[r]->(old) MERGE (other)-[new_r:TYPE(r)]->(canonical) SET new_r = properties(r)",
            
            f"MATCH (n {{name: '{name_a}'}}) WHERE n.name <> '{canonical_name}' DELETE n",
            f"MATCH (n {{name: '{name_b}'}}) WHERE n.name <> '{canonical_name}' DELETE n"
        ]
        
        for q in queries:
            try:
                self.client.execute_query(q)
            except Exception as e:
                logger.warning(f"Merge sub-query failed: {e}")
