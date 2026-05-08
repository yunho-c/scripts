"""Reverse the motion contained within a BVH file with respect to time."""

from pathlib import Path

import typer


app = typer.Typer(
    add_completion=False,
    help="Reverse BVH motion frames with respect to time.",
)


def reverse_bvh_time(input_path: str | Path, output_path: str | Path) -> None:
    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open("r") as f:
        lines = f.readlines()

    # Find where the actual motion data starts
    try:
        motion_index = lines.index("MOTION\n")
    except ValueError as exc:
        raise ValueError(
            f"BVH file does not contain a MOTION section: {input_path}"
        ) from exc

    # The two lines following "MOTION" are "Frames: X" and "Frame Time: X"
    data_start_index = motion_index + 3

    # Separate the header (Hierarchy + Motion setup) from the frame data
    header = lines[:data_start_index]
    frames = lines[data_start_index:]

    # Reverse the frame data array
    frames.reverse()

    # Write the new file
    with output_path.open("w") as f:
        f.writelines(header)
        f.writelines(frames)


@app.command()
def main(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the input BVH file.",
    ),
    output_path: Path = typer.Argument(
        ...,
        file_okay=True,
        dir_okay=False,
        writable=True,
        help="Path to write the reversed BVH file.",
    ),
) -> None:
    """Reverse the frame order in a BVH motion section."""
    try:
        reverse_bvh_time(input_path, output_path)
    except ValueError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Reversed BVH written to {output_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
