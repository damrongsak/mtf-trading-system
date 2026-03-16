import re
from typing import List, Dict, Set, Any
from app.core.logger import get_logger

logger = get_logger("QueryOptimizer")

def deduplicate_cypher_queries(queries: List[str]) -> List[str]:
    """
    Deduplicates Cypher queries by:
    1. Removing exact duplicates.
    2. Merging properties for identical MERGE (node) statements.
    """
    if not queries:
        return []

    unique_queries = []
    seen_exact = set()
    
    # Dictionary to store merged node properties: (Label, Name) -> {properties}
    # key: (Label, Name), value: dict of props
    node_merges = {}
    
    # Non-merge queries (CREATE, MATCH, etc. that aren't simple MERGE)
    other_queries = []

    # Regex for simple MERGE (Label {props})
    # Example: MERGE (n:Asset {name: 'XAUUSD', type: 'COMMODITY'})
    merge_pattern = re.compile(r'MERGE\s+\(\w+:(\w+)\s+\{(.+)\}\)')

    for q in queries:
        q = q.strip()
        if not q or q in seen_exact:
            continue
        
        seen_exact.add(q)
        
        match = merge_pattern.search(q)
        if match:
            label = match.group(1)
            props_str = match.group(2)
            
            # Extract name and other props
            # This is a bit naive but works for simple {key: 'val', key2: 'val2'}
            props = {}
            for prop_match in re.finditer(r'(\w+):\s*[\'"]?([^\'",}]+)[\'"]?', props_str):
                k, v = prop_match.groups()
                props[k] = v.strip()
            
            # We identify nodes primarily by 'name' or 'title'
            name = props.get('name') or props.get('title')
            
            if name:
                key = (label, name)
                if key not in node_merges:
                    node_merges[key] = props
                else:
                    # Merge properties, new ones take precedence if they differ? 
                    # Actually, we keep the first one or combine? Let's combine.
                    node_merges[key].update(props)
            else:
                other_queries.append(q)
        else:
            other_queries.append(q)

    # Reconstruct MERGE queries
    for (label, name), props in node_merges.items():
        props_list = []
        for k, v in props.items():
            # Escape single quotes in values
            v_escaped = str(v).replace("'", "\\'")
            props_list.append(f"{k}: '{v_escaped}'")
        
        props_joined = ", ".join(props_list)
        unique_queries.append(f"MERGE (n:{label} {{{props_joined}}})")

    # Add other unique queries (MATCH, CREATE relationships, etc.)
    for q in other_queries:
        unique_queries.append(q)
    
    return unique_queries
