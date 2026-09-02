import re

def convert_math_delimiters(text):
    # Convert display math \[ ... \] to $$ ... $$
    # flags=re.DOTALL allows matching across multiple lines
    converted_text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)

    # Convert inline math \( ... \) to $ ... $
    converted_text = re.sub(r'\\\((.*?)\\\)', r'$\1$', converted_text, flags=re.DOTALL)

    return converted_text

if __name__ == "__main__":
    # Example usage reading from and writing to a file
    input_file = "custom_syntax.md"
    output_file = "standard_markdown.md"

    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = convert_math_delimiters(content)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Conversion complete!")
