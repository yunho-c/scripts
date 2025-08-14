# glb_scaler.py
#
# A command-line script to scale 3D models in GLB/GLTF format.
#
# This script uses PyVista to read a model, apply a scaling transformation,
# and export the result to a new file.
#
# Dependencies:
#   pip install pyvista
#
# How to Run:
#   python glb_scaler.py input_model.glb output_model.glb --scale 1.0 1.0 2.0
#
# This example command would make the model twice as tall along the Z-axis.

import pyvista as pv
import argparse
import os


def scale_glb_model(input_path, output_path, scale_factors):
    """
    Loads a GLB model, scales it, and saves it to a new file.

    Args:
        input_path (str): The file path for the input GLB model.
        output_path (str): The file path for the scaled output GLB model.
        scale_factors (list[float]): A list of three floats for X, Y, Z scaling.
    """
    # --- 1. Input Validation ---
    if not os.path.exists(input_path):
        print(f"Error: Input file not found at '{input_path}'")
        return

    if len(scale_factors) != 3:
        print("Error: Please provide exactly three scale factors for X, Y, and Z.")
        return

    print(f"Loading model from: {input_path}")

    # --- 2. Read the Mesh ---
    # PyVista's read function automatically handles GLB/GLTF files.
    try:
        mesh = pv.read(input_path)
    except Exception as e:
        print(f"Error: Failed to read the model file. {e}")
        return

    print("Model loaded successfully.")
    print(f"Original Bounds: {mesh.bounds}")

    # --- 3. Apply Scaling ---
    # The scale() method modifies the mesh in place by default.
    mesh.scale(scale_factors, inplace=True)
    print(f"Applied scaling factors (X, Y, Z): {scale_factors}")
    print(f"New Scaled Bounds: {mesh.bounds}")

    # --- 4. Export the Scaled Mesh ---
    # To export to GLTF/GLB, we need to add the mesh to a Plotter scene.
    # Using off_screen=True prevents an interactive window from appearing.
    plotter = pv.Plotter(off_screen=True)
    plotter.add_mesh(mesh)  # Add the scaled mesh to the scene

    print(f"Exporting scaled model to: {output_path}")
    try:
        # The export_gltf function saves the scene to a file.
        plotter.export_gltf(output_path)
        print("Export complete!")
    except Exception as e:
        print(f"Error: Failed to export the model file. {e}")


def main():
    """
    Parses command-line arguments and runs the scaling function.
    """
    parser = argparse.ArgumentParser(
        description="A CLI tool to scale GLB/GLTF 3D models using PyVista.",
        formatter_class=argparse.RawTextHelpFormatter,  # For better help text formatting
    )

    parser.add_argument("input_file", help="Path to the input GLB/GLTF file.")

    parser.add_argument(
        "output_file", help="Path to save the scaled output GLB/GLTF file."
    )

    parser.add_argument(
        "--scale",
        nargs=3,  # Expect exactly 3 arguments for this flag
        type=float,
        metavar=("X", "Y", "Z"),
        default=[1.0, 1.0, 1.0],
        help="Scaling factors for the X, Y, and Z axes (e.g., 1.0 1.0 2.0).",
    )

    args = parser.parse_args()

    scale_glb_model(args.input_file, args.output_file, args.scale)


if __name__ == "__main__":
    # This ensures the main() function is called only when the script is executed directly
    main()
