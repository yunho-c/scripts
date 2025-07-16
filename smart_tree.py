#!/usr/bin/env python3
import os
from pathlib import Path

# --- Configuration ---
LIMIT = 20  # Max number of items to show before truncating.
PREVIEW = 3 # Number of example files to show for truncated directories.
# --- End Configuration ---

def smart_tree(directory: Path, prefix: str = ""):
    """Recursively prints a tree, truncating large directories."""
    # Get a sorted list of non-hidden items
    try:
        items = sorted([p for p in directory.iterdir() if not p.name.startswith('.')])
    except PermissionError:
        print(f"{prefix}└── [Permission Denied]")
        return

    item_count = len(items)

    if item_count > LIMIT:
        # It's large: show a preview and stop.
        for item in items[:PREVIEW]:
            print(f"{prefix}├── {item.name}")
        print(f"{prefix}└── ... ({item_count - PREVIEW} more items)")
    else:
        # It's small: list everything.
        for i, item in enumerate(items):
            is_last = (i == item_count - 1)
            connector = "└──" if is_last else "├──"
            new_prefix = "    " if is_last else "│   "

            print(f"{prefix}{connector} {item.name}")

            if item.is_dir():
                # It's a directory, so recurse.
                smart_tree(item, prefix + new_prefix)

if __name__ == "__main__":
    import sys
    start_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    print(str(start_path))
    smart_tree(start_path)
