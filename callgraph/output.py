"""Stage 3: turn a RepoGraph into JSON, DOT or an interactive HTML page."""
import json
import shutil
import subprocess
from pathlib import Path
from typing import List

from .models import Node, RepoGraph, make_ref

TEMPLATE = Path(__file__).parent / "graph_template.html"
MODULE_LEVEL = "<module>"


def node_to_dict(node: Node) -> dict:
    result = {
        "type": node.type,
        "content": node.content,
        "children": [node_to_dict(child) for child in node.children],
        "line_number": node.line_number,
        "end_line_number": node.end_line_number,
    }
    optional = {
        "function": node.function,
        "qualname": node.qualname,
        "resolved": node.resolved,
        "alias": node.alias.model_dump() if node.alias else None,
    }
    result.update({key: value for key, value in optional.items() if value})
    return result


def _edges_as_dicts(graph: RepoGraph) -> List[dict]:
    return [{"from": e.source, "to": e.target, "line": e.line} for e in graph.edges]


def to_json(graph: RepoGraph) -> str:
    return json.dumps({
        "entry": graph.entry,
        "files": {path: node_to_dict(f.tree) for path, f in graph.files.items()},
        "edges": _edges_as_dicts(graph),
    }, indent=2)


def to_dot(graph: RepoGraph) -> str:
    lines = ["digraph calls {", "  rankdir=LR;", "  node [shape=box, fontsize=10];"]
    for source, target in sorted({(e.source, e.target) for e in graph.edges}):
        lines.append(f'  "{source}" -> "{target}";')
    lines.append("}")
    return "\n".join(lines)


def to_html(graph: RepoGraph) -> str:
    """A self-contained page (no external libraries) built from graph_template.html."""
    used = {e.source for e in graph.edges} | {e.target for e in graph.edges}

    files = []
    for path, source in graph.files.items():
        nodes = []
        if make_ref(path, MODULE_LEVEL) in used:
            nodes.append({"id": make_ref(path, MODULE_LEVEL), "label": MODULE_LEVEL,
                          "type": "module", "line": None})
        by_line = sorted(source.defs.items(), key=lambda item: item[1].line_number or 0)
        for qualname, node in by_line:
            ref = make_ref(path, qualname)
            if node.type == "function" or ref in used:
                nodes.append({"id": ref, "label": qualname, "type": node.type, "line": node.line_number})
        files.append({"path": path, "nodes": nodes})

    data = {"entry": graph.entry, "files": files, "edges": _edges_as_dicts(graph)}
    payload = json.dumps(data).replace("</", "<\\/")  # keep the JSON from closing the <script> tag
    return TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)


def render_svg(dot_source: str, output_path: str):
    """Render DOT with Graphviz. Raises RuntimeError if Graphviz isn't installed."""
    if not shutil.which("dot"):
        raise RuntimeError("Graphviz 'dot' not found on PATH. Install it "
                           "(e.g. `winget install Graphviz.Graphviz`) or use --format html.")
    subprocess.run(["dot", "-Tsvg", "-o", output_path], input=dot_source, text=True, check=True)
