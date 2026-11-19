"""Run the pipeline: crawl local imports, parse each file, then resolve calls."""
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .models import RepoGraph, SourceFile
from .modules import ModuleResolver
from .parser import parse_file
from .resolver import CallResolver


def crawl(entry: str, modules: ModuleResolver) -> Dict[str, SourceFile]:
    """Parse the entry file and every repo file reachable through imports."""
    files: Dict[str, SourceFile] = {}
    pending: List[str] = [entry]

    while pending:
        path = pending.pop()
        if path in files:  # also stops circular imports
            continue
        source = _parse(path, modules)
        if source is None:
            continue
        files[path] = source
        pending.extend(p for p in source.local_imports if p not in files)
    return files


def _parse(path: str, modules: ModuleResolver) -> Optional[SourceFile]:
    try:
        text = (modules.root / path).read_text(encoding="utf-8")
        return parse_file(path, text, modules)
    except (SyntaxError, UnicodeDecodeError, OSError) as error:
        print(f"warning: skipping {path}: {error}", file=sys.stderr)
        return None


def build_graph(entry: str, root: Optional[str] = None) -> RepoGraph:
    entry_path = Path(entry).resolve()
    modules = ModuleResolver(Path(root) if root else entry_path.parent)

    entry_rel = modules.relative(entry_path)
    if entry_rel is None:
        raise ValueError(f"{entry} is outside root {modules.root}")

    files = crawl(entry_rel, modules)
    edges = CallResolver(files, modules).resolve_all()
    return RepoGraph(entry=entry_rel, files=files, edges=edges)
