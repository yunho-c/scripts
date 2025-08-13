import os
import argparse
import sys
import pyvista as pv


def generate_thumbnail(glb_path, output_path, resolution, overwrite=False):
    """
    Generates a thumbnail for a single .glb file using PyVista.

    Args:
        glb_path (str): The full path to the input .glb file.
        output_path (str): The full path for the output PNG thumbnail.
        resolution (int): The resolution (width and height) of the thumbnail.
        overwrite (bool): If True, overwrites the thumbnail if it already exists.
    """
    # Check if thumbnail already exists and if we should skip it
    if os.path.exists(output_path) and not overwrite:
        print(
            f"INFO: Thumbnail already exists for {os.path.basename(glb_path)}. Skipping."
        )
        return

    print(
        f"Processing: {os.path.basename(glb_path)} -> {os.path.basename(output_path)}"
    )

    try:
        # Set up the plotter for off-screen rendering
        plotter = pv.Plotter(off_screen=True, window_size=[resolution, resolution])
        # plotter = pv.Plotter(window_size=[resolution, resolution])  # DEBUG

        # Directly import GLTF/GLB
        plotter.import_gltf(glb_path)

        # Set the camera to an isometric view for a good default angle
        # Option 1
        plotter.camera.up = (0, 1, 0)  # NOTE: doesn't really work with isometric...
        # plotter.reset_camera(). # NOTE: didn't help
        # plotter.view_isometric()

        # Option 2
        plotter.view_vector(vector=[1, 1, 1], viewup=[0, 1, 0])

        # Optional: add XYZ axes annotation gizmo
        plotter.add_axes()

        # # Optional: Use parallel projection for a clearer, more technical look
        # plotter.enable_parallel_projection()

        # Take a screenshot and save it
        # plotter.show()  # DEBUG
        plotter.screenshot(output_path, transparent_background=True)

        # Clean up and close the plotter to free memory
        plotter.close()

        print(f"SUCCESS: Created thumbnail {os.path.basename(output_path)}")

    except Exception as e:
        print(
            f"ERROR: Could not process {os.path.basename(glb_path)}. Reason: {e}",
            file=sys.stderr,
        )


def main():
    """
    Main function to parse arguments and find .glb files to process.
    """
    parser = argparse.ArgumentParser(
        description="Recursively search for .glb files and generate thumbnails.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=os.getcwd(),
        help="The directory to search in. Defaults to the current working directory.",
    )

    parser.add_argument(
        "-r",
        "--resolution",
        type=int,
        default=512,
        help="Resolution of the thumbnail image (e.g., 512 for 512x512). Default is 512.",
    )

    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        # action="store_false",
        help="Force overwrite of existing thumbnails.",
    )

    args = parser.parse_args()

    # Validate that the input directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory not found at '{args.directory}'", file=sys.stderr)
        sys.exit(1)

    print("-" * 50)
    print(f"Starting thumbnail generation...")
    print(f"  Directory:   {args.directory}")
    print(f"  Resolution:  {args.resolution}x{args.resolution}")
    print(f"  Overwrite:   {args.overwrite}")
    print("-" * 50)

    # Recursively walk the directory
    file_count = 0
    for root, _, files in os.walk(args.directory):
        for file in files:
            # Check if the file has a .glb extension
            if file.lower().endswith(".glb"):
                file_count += 1
                glb_path = os.path.join(root, file)

                # Define the output path for the thumbnail (e.g., model.glb -> model.png)
                output_path = os.path.splitext(glb_path)[0] + ".png"

                generate_thumbnail(
                    glb_path, output_path, args.resolution, args.overwrite
                )

    if file_count == 0:
        print("No .glb files found in the specified directory.")
    else:
        print("-" * 50)
        print("Thumbnail generation complete.")


if __name__ == "__main__":
    main()
