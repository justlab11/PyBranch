# TraceExecution

Static call-graph extractor for Python repos. Point it at an entry file and it follows your local imports, parses every file it reaches, and links each function call to the definition it refers to, across files. The result is a graph you can export as JSON, Graphviz DOT, or an interactive HTML page.

It uses Python's `ast` module and never runs your code.

## Quick start

Requires Python 3.9+ and [pydantic](https://docs.pydantic.dev/) v2.

```bash
pip install pydantic
python -m callgraph test_codebase/main.py --format html -o graph.html
```

Open `graph.html` in a browser. Nothing is loaded from the internet.

## Usage

```
python -m callgraph ENTRY.py [--root DIR] [-o OUT] [--format json|dot|html|svg]
```

| Option | Description |
|---|---|
| `ENTRY` | Entry-point `.py` file. Crawling starts here. |
| `--root DIR` | Repo root used to resolve imports. Defaults to the entry file's folder. |
| `-o, --output` | Output file. Defaults to stdout (not allowed for `svg`). |
| `--format` | `json` (default), `dot`, `html`, or `svg`. |

`svg` renders through Graphviz, so `dot` must be on your PATH. If it isn't, use `html`, which needs no extra tools.

### Output formats

- **html**: a self-contained page. Files are boxes laid out in columns by distance from the entry file. Hover a function to highlight its callers and callees; click to pin the selection.
- **dot**: Graphviz source, one edge per caller/callee pair.
- **json**: the full node tree for each file plus the resolved edges.
- **svg**: DOT rendered by Graphviz.

Functions are identified as `path/to/file.py::Class.method`. Module-level code is `file.py::<module>`.

### Use it as a library

```python
from callgraph import build_graph

graph = build_graph("test_codebase/main.py")
for edge in graph.edges:
    print(edge.source, "->", edge.target, f"(line {edge.line})")
```

## What it resolves

| Case | Example |
|---|---|
| Local functions | `helper()` |
| Imported modules, with or without aliases | `import app.utils as u; u.fmt()` |
| Imported symbols, with or without aliases | `from app.utils import fmt as f; f()` |
| Relative imports | `from . import billing` |
| Re-exports through `__init__.py` | `from app import place_order` |
| Circular imports | `orders` <-> `notifications` |
| Methods on `self` and `cls` | `self.save()` |
| Inherited methods | `self.describe()` defined on a base class |
| `super()` calls | `super().__init__()` |
| Class instantiation | `Order(...)` links to `Order.__init__` |
| Nested functions | a function defined and called inside another |
| Async functions | `async def` is handled like `def` |

## Known limitations

- **No type tracking.** After `order = Order(...)`, the call `order.summary()` is not resolved, because the tool doesn't know what `order` is.
- **Star imports** (`from x import *`) can't be bound to names, so those calls stay unresolved.
- **Calls on expressions** like `foo().bar()` are skipped.
- **Dynamic behavior** (`getattr`, decorators that wrap functions, monkey-patching) is invisible to static analysis.
- **Imports inside functions** are not used for resolution.
- External and standard-library calls are ignored on purpose, so the graph only covers your repo.

## How it works

```
entry file
    |  crawl local imports
    v
parser.py     file -> Node tree + import table
    |
    v
resolver.py   each call -> the definition it refers to
    |
    v
output.py     json / dot / html / svg
```

| Module | Role |
|---|---|
| `models.py` | Shared types: `Node`, `ImportRef`, `Edge`, `SourceFile`, `RepoGraph` |
| `modules.py` | `ModuleResolver`: maps an import to a file in the repo |
| `parser.py` | `PyFileAnalyzer`: one file into a node tree |
| `resolver.py` | `CallResolver`: symbol lookup, inheritance, `self`/`super` handling |
| `analyzer.py` | `build_graph()`: runs the full pipeline |
| `output.py` | Exporters |
| `cli.py` | The command line |
| `graph_template.html` | Template for the HTML export |

## Try it on the sample project

[test_codebase/](test_codebase/) is a small order-processing app built to exercise every case above, plus a few unresolved ones on purpose (see the comments in `main.py`).

```bash
python -m callgraph test_codebase/main.py --format dot
```

## Project layout

```
callgraph/      the package
test_codebase/  sample project used for testing
```
