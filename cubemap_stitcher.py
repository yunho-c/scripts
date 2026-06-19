# Examples:
# python cubemap_stitcher.py /path/to/your/images
# or
# python cubemap_stitcher.py ./my_cubemap_folder --output ./final_skybox.jpg --width 4096 --ext .jpg


from pathlib import Path
from typing import Optional
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

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

@app.command()
def convert(
    input_dir: Path = typer.Argument(..., help="Directory containing the 6 cubemap images."),
    output_file: Path = typer.Option(Path("equirectangular.png"), "--output", "-o", help="Output file path."),
    width: int = typer.Option(2048, "--width", "-w", help="Output width (height is automatically set to width/2)."),
    ext: Optional[str] = typer.Option(None, "--ext", "-e", help="Image extension to look for. Defaults to common image formats.")
):
    """
    Combines 6 cubemap face images into a single equirectangular panoramic image.
    """
    if not input_dir.is_dir():
        typer.secho(f"Error: {input_dir} is not a valid directory.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    cubemap_dict = {}
    requested_ext = None
    if ext:
        requested_ext = ext.lower()
        if not requested_ext.startswith("."):
            requested_ext = f".{requested_ext}"

    # Scan the directory for files with either the requested extension or a
    # common image extension if no explicit filter was provided.
    for file_path in sorted(input_dir.iterdir()):
        if not file_path.is_file():
            continue

        file_ext = file_path.suffix.lower()
        if requested_ext:
            if file_ext != requested_ext:
                continue
        elif file_ext not in IMAGE_EXTENSIONS:
            continue

        filename = file_path.stem

        # Check if the filename ends with one of our suffixes
        for suffix, key in SUFFIX_TO_KEY.items():
            if filename.lower().endswith(suffix):
                img = Image.open(file_path).convert("RGB")
                cubemap_dict[key] = np.array(img)
                typer.echo(f"Found {suffix} face: {file_path.name}")
                break

    # Validate that we found all 6 required faces
    missing = set(SUFFIX_TO_KEY.values()) - set(cubemap_dict.keys())
    if missing:
        typer.secho(f"\nError: Missing faces mapped to {missing}.", fg=typer.colors.RED)
        extension_help = f" with extension {requested_ext}" if requested_ext else ""
        typer.secho(f"Ensure your target directory contains image files{extension_help} ending in _ft, _rt, _bk, _lf, _up, _dn.", fg=typer.colors.YELLOW)
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
