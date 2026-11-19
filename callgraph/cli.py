"""Command line entry point.

    python -m callgraph ENTRY.py [--root DIR] [-o OUT] [--format json|dot|html|svg]
"""
import argparse
import sys
from pathlib import Path

from .analyzer import build_graph
from .output import render_svg, to_dot, to_html, to_json

TEXT_FORMATS = {"json": to_json, "dot": to_dot, "html": to_html}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="callgraph",
        description="Extract a call graph from a Python file and its local imports.")
    parser.add_argument("entry", help="entry-point .py file")
    parser.add_argument("--root", help="repo root for resolving imports (default: entry's folder)")
    parser.add_argument("-o", "--output", help="output file (default: stdout)")
    parser.add_argument("--format", choices=[*TEXT_FORMATS, "svg"], default="json")
    args = parser.parse_args(argv)

    if args.format == "svg" and not args.output:
        parser.error("--format svg needs -o OUTPUT")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    graph = build_graph(args.entry, args.root)
    summary = f"Analyzed {len(graph.files)} file(s), {len(graph.edges)} resolved call(s)."

    if args.format == "svg":
        try:
            render_svg(to_dot(graph), args.output)
        except RuntimeError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(f"{summary} Rendered {args.output}")
        return 0

    text = TEXT_FORMATS[args.format](graph)
    if not args.output:
        print(text)
        return 0

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(text, encoding="utf-8")
    print(f"{summary} Saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
