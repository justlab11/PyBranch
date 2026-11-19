"""Data types shared by every stage of the pipeline."""
from typing import Dict, List, Optional

from pydantic import BaseModel


class Alias(BaseModel):
    actual_name: str
    alias_name: str
    local_file: bool
    target_file: Optional[str] = None


class Node(BaseModel):
    """One element of a file's syntax tree: function, class, import or call."""
    type: str
    content: str
    children: List['Node'] = []
    function: Optional[str] = None
    alias: Optional[Alias] = None
    line_number: Optional[int] = None
    end_line_number: Optional[int] = None
    bases: List[str] = []            # class nodes only
    qualname: Optional[str] = None   # function/class nodes: dotted name within the file
    resolved: Optional[str] = None   # call nodes: "file::qualname" of the target definition


class ImportRef(BaseModel):
    """What a name bound by an import statement refers to.

    import a.b      -> ImportRef(module="a")                       (binds "a")
    import a.b as c -> ImportRef(module="a.b", aliased=True)       (binds "c")
    from .x import y -> ImportRef(module="x", symbol="y", level=1) (binds "y")
    """
    module: str
    symbol: Optional[str] = None
    level: int = 0
    aliased: bool = False


class Edge(BaseModel):
    """A resolved call. `source` and `target` look like "file.py::Class.method"."""
    source: str
    target: str
    line: Optional[int] = None


class SourceFile(BaseModel):
    """Everything we know about one parsed file."""
    path: str
    tree: Node
    imports: Dict[str, ImportRef] = {}
    defs: Dict[str, Node] = {}           # qualname -> function/class node
    local_imports: List[str] = []        # repo files this file imports


class RepoGraph(BaseModel):
    entry: str
    files: Dict[str, SourceFile]
    edges: List[Edge]


def make_ref(file: str, qualname: str) -> str:
    return f"{file}::{qualname}"


def split_ref(ref: str):
    file, qualname = ref.split("::", 1)
    return file, qualname
