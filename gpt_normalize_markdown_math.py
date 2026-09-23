import re
from pathlib import Path
from typing import Optional

import typer


app = typer.Typer(help="Normalize GPT-style math delimiters in a Markdown file.")


# Match protected Markdown and math before considering damaged delimiters.
# Bare display math must occupy whole lines; ordinary [labels] stay intact.
_TOKENS = re.compile(
    r"(?P<fence>^ {0,3}(?P<marker>`{3,}|~{3,})[^\n]*\n"
    r".*?(?:^ {0,3}(?P=marker)[ \t]*(?=\n|\Z)|\Z))"
    r"|(?P<indented>^(?: {4}|\t)[^\n]*(?:\n|\Z))"
    r"|(?P<code>(?P<ticks>`+)(?!`).*?(?<!`)(?P=ticks)(?!`))"
    r"|(?P<reference>^ {0,3}\[[^\]\n]+\]:[^\n]*)"
    r"|(?P<link>!?\[(?:[^\[\]\n]|\[[^\]\n]*\])*\]"
    r"(?:\((?:[^()\n]|\([^()\n]*\))*\)|\[[^\]\n]*\]))"
    r"|(?P<dollars>(?<!\\)\$\$.*?(?<!\\)\$\$"
    r"|(?<![\\$])\$(?!\$)(?:\\[^\n]|[^$\n\\])+(?<!\\)\$(?!\$))"
    r"|(?<!\\)\\\[(?P<display>.*?)\\\]"
    r"|(?<!\\)\\\((?P<inline>.*?)\\\)"
    r"|(?P<bare_display>^ {0,3}(?:\#{1,6}[ \t]+)?\["
    r"(?P<bare_body>.*?)\][ \t]*(?=\n|\Z))"
    r"|(?P<bare_inline>(?<![\\\w])\((?:[^()\n]|\([^()\n]*\))*\))",
    re.MULTILINE | re.DOTALL,
)


def looks_like_math(body: str) -> bool:
    """Conservatively recognize bare math; prose parentheses are ambiguous."""
    body = body.strip()
    # Avoid file references, URLs, and prose even when they contain underscores.
    if not body or re.search(r"(?:https?://|/(?:Users|home|tmp)/)", body):
        return False
    without_commands = re.sub(r"\\[A-Za-z]+|&(?:[A-Za-z]+|#\d+);", "", body)
    without_text = re.sub(r"\{[^{}]*\}", "", without_commands)
    if re.search(r"[A-Za-z]{3,}", without_text):
        return False
    return bool(
        re.fullmatch(r"[A-Za-z]|\d+(?:\.\d+)?", body)
        or re.search(r"\\[A-Za-z]+|[_^=<>+]|\d\s*[-*/]\s*\d", body)
    )


def convert_math_delimiters(text: str, *, recover_bare: bool = True) -> str:
    """Normalize math to dollars, optionally recovering lost delimiter slashes.

    Recovery recognizes math-like (...) and whole-line [...] blocks, including
    blocks accidentally turned into Markdown headings. It changes delimiters
    only: missing operators or other damaged LaTeX must be repaired separately.
    """
    def replace(match: re.Match[str]) -> str:
        if match.group("display") is not None:
            return "$$\n" + match.group("display").strip() + "\n$$"
        if match.group("inline") is not None:
            return "$" + match.group("inline").strip() + "$"
        if recover_bare and match.group("bare_display") is not None:
            body = match.group("bare_body").strip()
            if looks_like_math(body):
                return "$$\n" + body + "\n$$"
        if recover_bare and match.group("bare_inline") is not None:
            body = match.group()[1:-1].strip()
            if looks_like_math(body):
                return "$" + body + "$"
        return match.group()

    return _TOKENS.sub(replace, text)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(
        f"{input_path.stem}_normalized{input_path.suffix}"
    )


@app.command()
def main(
    input_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Markdown file to normalize.",
    ),
    output_path: Optional[Path] = typer.Option(
        None,
        "--output",
        "--output-path",
        "-o",
        file_okay=True,
        dir_okay=False,
        help="Output path. Defaults to INPUT_normalized beside the input file.",
    ),
    recover_bare: bool = typer.Option(
        True,
        "--recover-bare/--no-recover-bare",
        help="Recover math-like (...) and whole-line [...] with missing backslashes.",
    ),
) -> None:
    """Normalize GPT-style math delimiters in a Markdown file."""
    destination = output_path or default_output_path(input_path)
    content = input_path.read_text(encoding="utf-8")
    destination.write_text(
        convert_math_delimiters(content, recover_bare=recover_bare), encoding="utf-8"
    )

    typer.echo(f"Normalized Markdown written to {destination}")


if __name__ == "__main__":
    app()
