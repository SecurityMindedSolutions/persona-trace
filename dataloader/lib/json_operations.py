#! /usr/bin/env python3


def deep_flatten(obj, parent_key='', sep='.'): 
    """Recursively flattens nested dicts and lists into a flat dict with path keys."""
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
            items.extend(deep_flatten(v, new_key, sep=sep).items())
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            new_key = f"{parent_key}[{idx}]"
            items.extend(deep_flatten(v, new_key, sep=sep).items())
    else:
        items.append((parent_key, obj))
    return dict(items)