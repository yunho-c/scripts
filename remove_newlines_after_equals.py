#!/usr/bin/env python3

import argparse
import sys
import os

def remove_newlines_after_equals(content: str) -> str:
    """
    Removes newline characters that immediately follow an equals sign.

    This function handles both Windows-style (`\r\n`) and Unix-style (`\n`)
    newlines to ensure cross-platform compatibility.

    Args:
        content: The string content to process.

    Returns:
        The processed string with the target newlines removed.
    """
    # It's important to replace the Windows-style newline ('\r\n') first.
    # If '\n' were replaced first, you might be left with a stray '\r'.
    processed_content = content.replace('=\r\n', '=')
    processed_content = processed_content.replace('=\n', '=')
    return processed_content

def main():
    """
    Main function to parse arguments and orchestrate the file processing.
    """
    # --- Argument Parser Setup ---
    # We set up a robust command-line interface to guide the user.
    parser = argparse.ArgumentParser(
        description="Removes newlines that occur immediately after an equals sign '='.",
        formatter_class=argparse.RawTextHelpFormatter, # Allows for better formatting in help text
        epilog="""
Examples of how to use the script:

1. Process an input file and print to console:
   python {prog} --file your_input_file.txt

2. Process an input file and save to an output file:
   python {prog} --file your_input_file.txt --output your_output_file.txt

3. Process a string directly from the command line:
   python {prog} --string "config_value =\\n'some value'"

4. Process a string and save to an output file:
   python {prog} --string "data =\\n12345" -o result.txt
""".format(prog=os.path.basename(sys.argv[0]))
    )

    # --- Mutually Exclusive Input Group ---
    # This ensures the user must provide one (and only one) input source.
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '-f', '--file',
        type=str,
        help="Path to the input file to process."
    )
    input_group.add_argument(
        '-s', '--string',
        type=str,
        help="An input string to process directly."
    )

    # --- Optional Output Argument ---
    parser.add_argument(
        '-o', '--output',
        type=str,
        help="Path to the output file. If not provided, result is printed to standard output."
    )

    args = parser.parse_args()

    # --- Read Input Content ---
    input_content = ""
    if args.string:
        # Use the string provided in the command-line arguments.
        input_content = args.string
    elif args.file:
        # Check if the file exists before trying to open it.
        if not os.path.exists(args.file):
            print(f"Error: Input file not found at '{args.file}'", file=sys.stderr)
            sys.exit(1)
        # Read the content from the specified file.
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                input_content = f.read()
        except Exception as e:
            print(f"Error: Could not read file '{args.file}'. Reason: {e}", file=sys.stderr)
            sys.exit(1)

    # --- Process the Content ---
    modified_content = remove_newlines_after_equals(input_content)

    # --- Write Output ---
    if args.output:
        # Write the modified content to the specified output file.
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"Success! Processed content has been saved to '{args.output}'")
        except Exception as e:
            print(f"Error: Could not write to file '{args.output}'. Reason: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # If no output file is specified, print the result to standard output.
        # This allows for piping to other commands.
        sys.stdout.write(modified_content)

if __name__ == "__main__":
    # This standard Python construct ensures the main() function is called
    # only when the script is executed directly.
    main()
