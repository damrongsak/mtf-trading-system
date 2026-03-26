"""
Standardized Ontology for Project Olympus Knowledge Graph.
Defines the allowed Node types, Relationship types, and their properties.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# --- Allowed Labels and Types ---

NodeLabel = Literal[
    "Paper", "Asset", "Concept", "MacroIndicator", 
    "Event", "Strategy", "Organization", "Country", 
    "Person", "SMC_Pattern", "Timeframe"
]

RelationshipType = Literal[
    "MENTIONS", "INFLUENCES", "SUPPORTS", "CONTRADICTS", 
    "TRIGGERS", "CORRELATES_WITH", "PROPOSES_STRATEGY", 
    "AFFECTS", "LEADS_TO", "OBSERVED_IN", "HEDGE_AGAINST", "LIQUIDATES"
]

# --- Schema Definitions ---

class NodeSchema(BaseModel):
    """Blueprint for a single node in the graph"""
    label: NodeLabel = Field(..., description="The classification of the entity")
    name: str = Field(..., description="The primary identifier/name of the entity (use PascalCase or formal names)")
    properties: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional context (e.g., type, source, value, confidence)"
    )

class RelationshipSchema(BaseModel):
    """Blueprint for a relationship between two nodes"""
    from_node: str = Field(..., description="The 'name' of the source node")
    to_node: str = Field(..., description="The 'name' of the target node")
    type: RelationshipType = Field(..., description="The type of the relationship")
    properties: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Relationship metadata (e.g., confidence, source_ref, impact)"
    )

class GraphExtractionSchema(BaseModel):
    """Final output schema for the LLM to provide structured data"""
    nodes: List[NodeSchema] = Field(default_factory=list, description="List of entities identified")
    relationships: List[RelationshipSchema] = Field(default_factory=list, description="List of connections identified")
    
    def to_cypher(self) -> List[str]:
        """Convert structured schema into valid Cypher queries"""
        queries = []
        
        # 1. Create Nodes
        for node in self.nodes:
            safe_name = node.name.replace("'", "\\'")
            props_list = [f"name: '{safe_name}'"]
            for k, v in node.properties.items():
                if isinstance(v, str):
                    v = v.replace("'", "\\'")
                props_list.append(f"{k}: '{v}'")
            
            props_str = ", ".join(props_list)
            queries.append(f"MERGE (n:{node.label} {{{props_str}}})")
            
        # 2. Create Relationships
        for rel in self.relationships:
            # Metadata for relationships
            props_list = []
            for k, v in rel.properties.items():
                if isinstance(v, str):
                    v = v.replace("'", "\\'")
                props_list.append(f"{k}: '{v}'")
            
            props_str = f" {{{', '.join(props_list)}}}" if props_list else ""
            
            safe_from = rel.from_node.replace("'", "\\'")
            safe_to = rel.to_node.replace("'", "\\'")
            
            queries.append(
                f"MATCH (a), (b) WHERE a.name = '{safe_from}' "
                f"AND b.name = '{safe_to}' "
                f"MERGE (a)-[:{rel.type}{props_str}]->(b)"
            )
            
        return queries
