#!/usr/bin/env python3
import os
import stat
import argparse
from pathlib import Path
from rich.console import Console
from rich.text import Text

# --- Configuration ---
COMPRESSED_EXTENSIONS = {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z"}
# --- End Configuration ---

console = Console()


def get_file_style(path: Path) -> str:
    """Determines the rich style for a given file path."""
    if path.is_dir():
        return "bold blue"

    # Check for compressed files by extension
    if path.suffix.lower() in COMPRESSED_EXTENSIONS:
        return "bold red"

    # Check for executable permissions (for non-Windows systems)
    try:
        if os.name != "nt" and (path.stat().st_mode & stat.S_IXUSR):
            return "bold green"
    except (OSError, PermissionError):
        # Ignore if we can't stat the file
        pass

    # Default style for regular files
    return ""


def smart_tree(
    directory: Path, prefix: str = "", filelimit: int | None = None, preview: int = 3
):
    """Recursively prints a tree, truncating large directories and adding color."""
    try:
        # Get a sorted list of non-hidden items
        items = sorted([p for p in directory.iterdir() if not p.name.startswith(".")])
    except PermissionError:
        console.print(f"{prefix}└── [Permission Denied]", style="dim")
        return

    item_count = len(items)

    # Truncate only if filelimit is set and the count is exceeded
    if filelimit is not None and item_count > filelimit:
        # It's large: show a preview and stop.
        for item in items[:preview]:
            style = get_file_style(item)
            console.print(f"{prefix}├── ", Text(item.name, style=style))
        console.print(
            f"{prefix}└── ... ({item_count - preview} more items)", style="dim"
        )
    else:
        # It's small or no limit is set: list everything.
        for i, item in enumerate(items):
            is_last = i == item_count - 1
            connector = "└──" if is_last else "├──"
            new_prefix = "    " if is_last else "│   "

            style = get_file_style(item)
            console.print(f"{prefix}{connector}", Text(item.name, style=style))

            if item.is_dir():
                # It's a directory, so recurse with the same settings.
                smart_tree(
                    item, prefix + new_prefix, filelimit=filelimit, preview=preview
                )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A 'smart' tree command that can truncate large directories.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="The directory to start the tree from.\nDefaults to the current directory.",
    )
    parser.add_argument(
        "--filelimit",
        type=int,
        default=None,
        help="Maximum number of items to show in a directory before truncating.\nNo limit by default.",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=3,
        help="Number of example files to show for truncated directories.\nDefault is 3.",
    )
    args = parser.parse_args()

    start_path = Path(args.path).resolve()

    # Print the root directory
    console.print(str(start_path), style="bold magenta")

    # Start the tree traversal with the parsed arguments
    smart_tree(start_path, filelimit=args.filelimit, preview=args.preview)
