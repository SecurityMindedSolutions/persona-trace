#! /usr/bin/env python3


def deep_flatten(obj, parent_key='', sep='.'): 
    """Recursively flattens nested dicts and lists into a flat dict with path keys."""
    items = []
    if isinstance(obj, dict):
        # Skip empty dictionaries
        if not obj:
            return {}
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
            items.extend(deep_flatten(v, new_key, sep=sep).items())
    elif isinstance(obj, list):
        # Skip empty lists
        if not obj:
            return {}
        # For lists, create a multi-line string with each item on its own line
        if all(isinstance(item, (str, int, float, bool)) for item in obj):
            # Simple list of primitives - one per line
            items.append((parent_key, '\n'.join(str(item) for item in obj)))
        elif all(isinstance(item, dict) for item in obj):
            # List of objects - each object as a compact JSON string on its own line
            import json
            summaries = []
            for item in obj:
                # Create a compact JSON representation of the object
                compact_json = json.dumps(item, separators=(',', ':'), ensure_ascii=False)
                summaries.append(compact_json)
            items.append((parent_key, '\n'.join(summaries)))
        else:
            # Mixed list - each item on its own line
            items.append((parent_key, '\n'.join(str(item) for item in obj)))
    else:
        items.append((parent_key, obj))
    return dict(items)