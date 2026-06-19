# Examples:
# python cubemap_stitcher.py /path/to/your/images
# or
# python cubemap_stitcher.py ./my_cubemap_folder --output ./final_skybox.jpg --width 4096 --ext .jpg


import os
from pathlib import Path
import typer
import numpy as np
from PIL import Image
import py360convert

app = typer.Typer(help="Convert a 6-face cubemap to an equirectangular image.")

# Mapping your suffixes to py360convert's expected face keys
SUFFIX_TO_KEY = {
    "_ft": "F", # Front
    "_rt": "R", # Right
    "_bk": "B", # Back
    "_lf": "L", # Left
    "_up": "U", # Up
    "_dn": "D"  # Down
}

@app.command()
def convert(
    input_dir: Path = typer.Argument(..., help="Directory containing the 6 cubemap images."),
    output_file: Path = typer.Option(Path("equirectangular.png"), "--output", "-o", help="Output file path."),
    width: int = typer.Option(2048, "--width", "-w", help="Output width (height is automatically set to width/2)."),
    ext: str = typer.Option(".png", "--ext", "-e", help="Image extension to look for (e.g. .png, .jpg).")
):
    """
    Combines 6 cubemap face images into a single equirectangular panoramic image.
    """
    if not input_dir.is_dir():
        typer.secho(f"Error: {input_dir} is not a valid directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    cubemap_dict = {}

    # Scan the directory for files with the required extension
    for file_path in input_dir.glob(f"*{ext}"):
        filename = file_path.stem

        # Check if the filename ends with one of our suffixes
        for suffix, key in SUFFIX_TO_KEY.items():
            if filename.endswith(suffix):
                img = Image.open(file_path).convert("RGB")
                cubemap_dict[key] = np.array(img)
                typer.echo(f"Found {suffix} face: {file_path.name}")
                break

    # Validate that we found all 6 required faces
    missing = set(SUFFIX_TO_KEY.values()) - set(cubemap_dict.keys())
    if missing:
        typer.secho(f"\nError: Missing faces mapped to {missing}.", fg=typer.colors.RED)
        typer.secho("Ensure your target directory contains files ending in _ft, _rt, _bk, _lf, _up, _dn.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)

    typer.echo("\nAll 6 faces loaded. Generating equirectangular image...")

    # Equirectangular images are strictly a 2:1 aspect ratio
    height = width // 2

    try:
        # Perform the Cubemap to Equirectangular (c2e) conversion
        equirect_array = py360convert.c2e(cubemap_dict, h=height, w=width, cube_format='dict')
    except Exception as e:
        typer.secho(f"Conversion failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # Convert the numpy array back to an image and save it
    out_img = Image.fromarray(equirect_array)
    out_img.save(output_file)
    typer.secho(f"\nSuccess! Saved to {output_file}", fg=typer.colors.GREEN)

if __name__ == "__main__":
    app()
