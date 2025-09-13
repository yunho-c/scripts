#!/usr/bin/env python3
"""
Usage:

python sync_folders.py ./project-original ./project-ported --dry-run
    *(You can also use the shorthand `-d` for `--dry-run`)*

python sync_folders.py ./project-original ./project-ported
    You will see a prompt: `Do you want to proceed with the sync operations? [y/n] (n):`

python sync_folders.py ./project-original ./project-ported --force
    *(You can also use the shorthand `-f` for `--force`)*
"""
import argparse
import datetime
import os
import shutil
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.prompt import Confirm
from rich.table import Table

# Initialize Rich console for pretty printing
console = Console()


def get_file_map(root_dir: str) -> dict:
    """
    Crawls a directory tree and returns a dictionary mapping each file's
    relative path to its absolute path and modification time.
    """
    file_map = {}
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            absolute_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(absolute_path, root_dir).replace("\\", "/")
            mtime = os.path.getmtime(absolute_path)
            file_map[relative_path] = {"abs_path": absolute_path, "mtime": mtime}
    return file_map


def format_time(timestamp: float) -> str:
    """Formats a timestamp for display."""
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


def compare_and_suggest_sync(dir1: str, dir2: str) -> list[tuple[str, str, str]]:
    """
    Compares two directories and returns a list of suggested file sync operations.
    A report table is printed to the console.

    Args:
        dir1 (str): The path to the first directory.
        dir2 (str): The path to the second directory.

    Returns:
        A list of suggested operations. Each operation is a tuple
        in the format ('COPY', 'source_path', 'destination_path').
    """
    dir1_abs = os.path.abspath(dir1)
    dir2_abs = os.path.abspath(dir2)

    panel = Panel(
        f"[bold]Source (DIR 1):[/bold] [cyan]{dir1_abs}[/]\n"
        f"[bold]Target (DIR 2):[/bold] [cyan]{dir2_abs}[/]",
        title="[yellow]Comparing Directories[/]",
        box=box.ROUNDED,
        expand=False,
    )
    console.print(panel)

    dir1_files = get_file_map(dir1)
    dir2_files = get_file_map(dir2)

    dir1_rel_paths = set(dir1_files.keys())
    dir2_rel_paths = set(dir2_files.keys())

    common_files = dir1_rel_paths.intersection(dir2_rel_paths)
    only_in_dir1 = dir1_rel_paths - dir2_rel_paths
    only_in_dir2 = dir2_rel_paths - dir1_rel_paths

    suggestions = []

    # Create a table to display the results
    table = Table(
        title="[bold]Sync Analysis Report[/]",
        box=box.HEAVY_HEAD,
        header_style="bold magenta",
    )
    table.add_column("Action", style="cyan", justify="right")
    table.add_column("Relative Path", style="green")
    table.add_column("Reason", style="yellow")

    # --- 1. Compare common files based on modification time ---
    for rel_path in sorted(list(common_files)):
        file1 = dir1_files[rel_path]
        file2 = dir2_files[rel_path]

        # Use a 1-second tolerance for filesystem differences
        if abs(file1["mtime"] - file2["mtime"]) > 1:
            if file1["mtime"] > file2["mtime"]:
                reason = f"Newer in DIR 1 ({format_time(file1['mtime'])} > {format_time(file2['mtime'])})"
                table.add_row("COPY DIR 1 -> 2", rel_path, reason)
                suggestions.append(("COPY", file1["abs_path"], file2["abs_path"]))
            else:
                reason = f"Newer in DIR 2 ({format_time(file2['mtime'])} > {format_time(file1['mtime'])})"
                table.add_row("COPY DIR 2 -> 1", rel_path, reason)
                suggestions.append(("COPY", file2["abs_path"], file1["abs_path"]))

    # --- 2. Report files that only exist in one directory ---
    for rel_path in sorted(list(only_in_dir1)):
        path1 = dir1_files[rel_path]["abs_path"]
        path2 = os.path.join(dir2, rel_path)
        table.add_row("COPY DIR 1 -> 2", rel_path, "Only in DIR 1")
        suggestions.append(("COPY", path1, path2))

    for rel_path in sorted(list(only_in_dir2)):
        path2 = dir2_files[rel_path]["abs_path"]
        path1 = os.path.join(dir1, rel_path)
        table.add_row("COPY DIR 2 -> 1", rel_path, "Only in DIR 2")
        suggestions.append(("COPY", path2, path1))

    if not suggestions:
        console.print(
            "\n[bold green]✅ Directories are perfectly in sync![/bold green]"
        )
    else:
        console.print(table)

    return suggestions


def execute_sync(suggestions: list[tuple[str, str, str]]):
    """
    Executes the copy operations with a progress bar.

    Args:
        suggestions: A list of tuples, e.g., [('COPY', 'src', 'dest')].
    """
    console.print(
        f"\n[bold yellow]Found {len(suggestions)} operations to perform.[/bold yellow]"
    )

    try:
        # Use a rich progress bar while iterating through operations
        for action, src, dest in track(
            suggestions, description="[bold green]Syncing files...[/]"
        ):
            if action == "COPY":
                try:
                    dest_dir = os.path.dirname(dest)
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(src, dest)  # copy2 preserves metadata
                except Exception as e:
                    console.print(f"  [bold red]❌ ERROR copying '{src}': {e}[/]")
            else:
                console.print(
                    f"  [bold orange_red1]⚠️ WARNING: Unknown action '{action}' for '{src}'. Skipping.[/]"
                )
        console.print(
            "\n[bold green]✅ Sync execution finished successfully![/bold green]"
        )
    except Exception as e:
        console.print(
            f"\n[bold red]❌ An unexpected error occurred during sync: {e}[/]"
        )


def main():
    """Main function to parse arguments and run the sync process."""
    parser = argparse.ArgumentParser(
        description="A CLI tool to compare two folders and suggest/execute sync operations based on file modification times.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("dir1", help="Path to the source directory (DIR 1).")
    parser.add_argument("dir2", help="Path to the target directory (DIR 2).")
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Execute sync without the confirmation prompt. Use with caution.",
    )

    args = parser.parse_args()

    # --- Validate Paths ---
    if not os.path.isdir(args.dir1):
        console.print(f"[bold red]Error: Directory not found at '{args.dir1}'[/]")
        exit(1)
    if not os.path.isdir(args.dir2):
        console.print(f"[bold red]Error: Directory not found at '{args.dir2}'[/]")
        exit(1)

    # --- Run Comparison ---
    sync_suggestions = compare_and_suggest_sync(args.dir1, args.dir2)

    # --- Handle Execution ---
    if not sync_suggestions:
        return  # Nothing to do

    if args.dry_run:
        console.print("\n[bold yellow]-- Dry Run Mode --[/] No files were changed.")
        return

    # If not a dry run, proceed to execution
    if args.force or Confirm.ask(
        "\n[bold]Do you want to proceed with the sync operations?[/bold]", default=False
    ):
        execute_sync(sync_suggestions)
    else:
        console.print("\n[bold red]Sync aborted by user.[/]")


if __name__ == "__main__":
    main()
