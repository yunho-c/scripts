"""
A script to synchronize Jupyter notebooks (.ipynb) and Python scripts (.py).

This script scans a specified directory for pairs of .py and .ipynb files
with the same base name. It then compares their last modification times
and syncs the newer file to the older one using `jupytext`, including
the modification timestamp.

This is useful for those who prefer to track Jupyter Notebooks in .py files.

Usage:
    python sync_jupyter.py [DIRECTORY] [-y/--yes]

Arguments:
    DIRECTORY: The directory to scan for files. Defaults to the current directory.
    -y, --yes: Skip the confirmation prompt and sync files directly.

Author: Yunho Cho
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.prompt import Confirm
except ImportError:
    print("Error: The 'rich' library is required. Please install it using 'pip install rich'", file=sys.stderr)
    sys.exit(1)

def find_and_compare_files(directory: Path):
    """Finds and compares modification times of .py and .ipynb file pairs."""
    file_pairs = {}
    # Group files by their base name (e.g., 'notebook' for 'notebook.py' and 'notebook.ipynb')
    for f in directory.glob('*.py'):
        file_pairs.setdefault(f.stem, {})['py'] = f
    for f in directory.glob('*.ipynb'):
        file_pairs.setdefault(f.stem, {})['ipynb'] = f

    operations = []
    for base, files in file_pairs.items():
        if 'py' in files and 'ipynb' in files:
            py_file = files['py']
            ipynb_file = files['ipynb']

            py_mtime = py_file.stat().st_mtime
            ipynb_mtime = ipynb_file.stat().st_mtime

            source, dest = None, None
            if py_mtime > ipynb_mtime:
                source, dest = py_file, ipynb_file
            elif ipynb_mtime > py_mtime:
                source, dest = ipynb_file, py_file

            if source and dest:
                operations.append({
                    "source": source,
                    "dest": dest,
                    "source_mtime": datetime.fromtimestamp(source.stat().st_mtime),
                    "dest_mtime": datetime.fromtimestamp(dest.stat().st_mtime),
                })
    return operations

def main():
    """Main function to run the sync script."""
    parser = argparse.ArgumentParser(
        description="Sync .py and .ipynb files in a specified directory based on the most recent update time."
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="The directory to scan for files. Defaults to the current directory."
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip the confirmation prompt and sync files directly."
    )
    args = parser.parse_args()

    console = Console()

    target_dir = Path(args.directory).resolve()

    if not target_dir.is_dir():
        console.print(f"[bold red]Error:[/bold red] The specified path '{args.directory}' is not a valid directory.")
        sys.exit(1)

    console.print(f"Scanning directory: [cyan]{target_dir}[/cyan]")

    with console.status("[bold green]Scanning for files...[/]"):
        operations = find_and_compare_files(target_dir)

    if not operations:
        console.print("[bold green]✓ All files are in sync. Nothing to do.[/]")
        return

    # --- Dry Run Table ---
    table = Table(
        title=f"[bold yellow]File Synchronization Plan for '{target_dir.name}' (Dry Run)[/]",
        title_style="yellow",
        header_style="bold cyan"
    )
    table.add_column("Action", style="red", justify="center")
    table.add_column("Newer File (Source)", style="green")
    table.add_column("Last Modified", style="dim")
    table.add_column("Older File (Destination)", style="red")
    table.add_column("Last Modified", style="dim")

    for op in operations:
        table.add_row(
            "OVERWRITE",
            op['source'].name,
            op['source_mtime'].strftime('%Y-%m-%d %H:%M:%S'),
            op['dest'].name,
            op['dest_mtime'].strftime('%Y-%m-%d %H:%M:%S'),
        )

    console.print(table)
    console.print()

    # --- Confirmation and Execution ---
    if args.yes or Confirm.ask("[bold]Do you want to apply these changes?[/]"):
        console.print("\n[bold]Starting synchronization...[/]")
        with console.status("[bold green]Syncing files with jupytext...[/]") as status:
            for op in operations:
                source, dest = op['source'], op['dest']
                status.update(f"[bold green]Syncing[/] [cyan]{source.name}[/] -> [cyan]{dest.name}[/]")
                try:
                    # Use jupytext to sync. We can point to either file in the pair.
                    # Jupytext will find the other and sync the older one.
                    subprocess.run(
                        ['jupytext', '--sync', str(source)],
                        check=True,
                        capture_output=True, # To hide jupytext output unless there's an error
                        text=True
                    )

                    # Set the access and modification times of the destination file to match the source file
                    source_stats = source.stat()
                    # This will make the destination file's atime and mtime identical to the source file's
                    os.utime(dest, (source_stats.st_atime, source_stats.st_mtime))
                except FileNotFoundError:
                    console.print("[bold red]Error: 'jupytext' command not found.[/bold red]")
                    console.print("Please install jupytext: [cyan]pip install jupytext[/cyan]")
                    sys.exit(1)
                except subprocess.CalledProcessError as e:
                    console.print(f"[bold red]Error syncing {source.name}:[/bold red]")
                    console.print(e.stderr)
                    sys.exit(1)
        console.print("[bold green]✓ Synchronization complete![/]")
    else:
        console.print("[bold red]✗ Operation cancelled.[/]")


if __name__ == "__main__":
    main()
