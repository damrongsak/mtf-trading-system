from typing import List, Optional
import re
from app.core.logging_config import get_logger

logger = get_logger("QueryOptimizer")


def deduplicate_cypher_queries(queries: Optional[List[str]]) -> List[str]:
    """
    Deduplicates Cypher queries by:
    1. Removing exact duplicates.
    2. Merging properties for identical MERGE (node) statements.
    """
    if queries is None:
        return []
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
    # Anchored with ^ and $ to ensure it only matches standalone node MERGE statements
    merge_pattern = re.compile(r"^MERGE\s+\(\w+:(\w+)\s+\{(.+?)\}\)$", re.IGNORECASE)

    for q in queries:
        q = q.strip()
        if not q or q in seen_exact:
            continue

        seen_exact.add(q)

        match = merge_pattern.match(q)
        if match:
            label = match.group(1)
            props_str = match.group(2)

            # Extract name and other props
            # Robust property parser that handles quoted strings and escaped characters
            props = {}
            # Regex for key: value where value can be a single/double quoted string or unquoted value
            prop_regex = re.compile(
                r'(\w+):\s*(\'(?:[^\'\\]|\\.)*\'|"(?:[^"\\]|\\.)*"|[^\'",}]+)'
            )
            for prop_match in prop_regex.finditer(props_str):
                k, v = prop_match.groups()
                # Remove quotes from the extracted value
                if v.startswith(("'", '"')) and v.endswith(v[0]):
                    v = v[1:-1]
                # Unescape escaped characters
                v = v.replace("\\'", "'").replace('\\"', '"')
                props[k] = v.strip()

            # We identify nodes primarily by 'name' or 'title'
            name = props.get("name") or props.get("title")

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
