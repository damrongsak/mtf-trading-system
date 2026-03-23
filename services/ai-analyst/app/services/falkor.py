import os
import logging
from typing import Any, Dict, Optional
from falkordb import FalkorDB

logger = logging.getLogger(__name__)

class FalkorService:
    """
    Bridge service for FalkorDB Knowledge Graph.
    Used for retrieving semantic context and knowledge scores for signals/trades.
    """
    def __init__(self, url: str = None, graph_name: str = None):
        self.url = url or os.getenv("FALKORDB_URL", "redis://falkordb:6379")
        self.graph_name = graph_name or os.getenv("GRAPH_NAME", "OlympusKnowledgeGraph")
        self.db = None
        self.graph = None
        
    def connect(self):
        """Initializes connection to FalkorDB."""
        try:
            self.db = FalkorDB.from_url(self.url)
            self.graph = self.db.select_graph(self.graph_name)
            logger.info(f"✅ Connected to FalkorDB at {self.url} (Graph: {self.graph_name})")
        except Exception as e:
            logger.error(f"❌ Failed to connect to FalkorDB: {e}")
            raise

    async def query_context(self, symbol: str) -> Dict[str, Any]:
        """
        Retrieves semantic context for a specific symbol.
        Supports both 'Asset' and 'Symbol' labels and pulls related concepts/strategies.
        """
        if not self.graph:
            self.connect()
            
        try:
            # Enhanced Cypher query to get related concepts, strategies, and risks
            # Supports multi-hop (e.g., Asset -> Concept -> Strategy)
            query = f"""
            MATCH (s) WHERE (s:Symbol OR s:Asset) AND s.name = '{symbol}'
            OPTIONAL MATCH (s)-[r1]-(n)
            OPTIONAL MATCH (n)-[r2]-(m) WHERE NOT m = s
            RETURN s.name as symbol, 
                   collect(distinct {{relation: type(r1), type: labels(n)[0], properties: properties(n)}}) as direct_entities,
                   collect(distinct {{relation: type(r2), type: labels(m)[0], properties: properties(m)}}) as indirect_entities
            """
            result = self.graph.query(query)
            
            context_data = {
                "symbol": symbol,
                "timestamp": None,
                "entities": [],
                "summary": "No semantic context found in Knowledge Graph."
            }
            
            if result.result_set:
                row = result.result_set[0]
                direct = [e for e in row[1] if e["relation"] is not None]
                indirect = [e for e in row[2] if e["relation"] is not None]
                
                # Merge and deduplicate by node name in properties
                all_entities = direct + indirect
                unique_entities = {}
                for e in all_entities:
                    name = e["properties"].get("name")
                    if name and name not in unique_entities:
                        unique_entities[name] = e
                
                context_data["entities"] = list(unique_entities.values())
                context_data["summary"] = f"Found {len(context_data['entities'])} unique semantic insights in Knowledge Graph."
                
            return context_data
            
        except Exception as e:
            logger.error(f"Error querying FalkorDB for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "summary": "Knowledge Graph query failed."
            }

    async def get_knowledge_score(self, symbol: str, context: Dict[str, Any]) -> float:
        """
        Calculates a semantic multiplier (0.5x to 1.5x) based on the context.
        Initial implementation: Simple count-based or probability-based score.
        """
        # Placeholder logic: 1.0 (Neutral) if no entities, otherwise 1.1 if we have links.
        # Phase 9.2 will implement LLM-based semantic scoring.
        if not context.get("entities"):
            return 1.0
            
        return 1.1 # Default small boost for having knowledge context
