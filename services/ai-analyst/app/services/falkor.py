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
        Returns a dictionary containing knowledge nodes and relationships.
        """
        if not self.graph:
            self.connect()
            
        try:
            # Basic Cypher query to get related concepts for the symbol
            # Note: The schema in FalkorDB is built by knowledge-ingestor.
            # We assume nodes like (s:Symbol {name: 'XAUUSD'}) exist.
            query = f"""
            MATCH (s:Symbol {{name: '{symbol}'}})-[r]-(n)
            RETURN s.name as symbol, type(r) as rel, properties(n) as node_props, labels(n) as labels
            LIMIT 10
            """
            result = self.graph.query(query)
            
            context_data = {
                "symbol": symbol,
                "timestamp": None, # Will be filled by caller
                "entities": [],
                "summary": "No semantic context found in Knowledge Graph."
            }
            
            if result.result_set:
                entities = []
                for row in result.result_set:
                    entities.append({
                        "relation": row[1],
                        "properties": row[2],
                        "type": row[3][0] if row[3] else "Unknown"
                    })
                context_data["entities"] = entities
                context_data["summary"] = f"Found {len(entities)} semantic relationships in Knowledge Graph."
                
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
