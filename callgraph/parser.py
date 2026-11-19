"""Stage 1: turn one source file into a Node tree plus its import table."""
import ast
from typing import Dict, List, Optional

from .models import Alias, ImportRef, Node, SourceFile
from .modules import ModuleResolver


class PyFileAnalyzer(ast.NodeVisitor):
    def __init__(self, source: str, path: str, modules: ModuleResolver):
        self.lines = source.splitlines()
        self.path = path
        self.modules = modules

        self.root = Node(type="module", content="")
        self.current = self.root
        self.scope: List[str] = []              # names of enclosing defs, outermost first
        self.imports: Dict[str, ImportRef] = {}
        self.local_imports: List[str] = []

    # ---- helpers ----
    def _source_span(self, node) -> str:
        return " ".join(self.lines[node.lineno - 1:node.end_lineno]).strip()

    def _dotted_name(self, node) -> Optional[str]:
        """`a.b.c` for a chain of names/attributes, else None."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            head = self._dotted_name(node.value)
            return f"{head}.{node.attr}" if head else None
        return None

    def _call_name(self, func) -> Optional[str]:
        """Name of the callee. Calls on arbitrary expressions get an `<expr>` prefix."""
        if isinstance(func, ast.Name):
            return func.id
        if not isinstance(func, ast.Attribute):
            return None
        dotted = self._dotted_name(func)
        if dotted:
            return dotted
        if self._is_super_call(func.value):
            return f"super.{func.attr}"
        return f"<expr>.{func.attr}"

    @staticmethod
    def _is_super_call(node) -> bool:
        return (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "super")

    # ---- definitions ----
    def _visit_definition(self, node, type_: str, **extra):
        self.scope.append(node.name)
        definition = Node(
            type=type_,
            content=self.lines[node.lineno - 1].strip(),
            line_number=node.lineno,
            end_line_number=node.end_lineno,
            qualname=".".join(self.scope),
            **extra,
        )
        self.current.children.append(definition)

        parent, self.current = self.current, definition
        self.generic_visit(node)
        self.current = parent
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self._visit_definition(node, "function", function=node.name)

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_ClassDef(self, node):
        bases = [name for name in map(self._dotted_name, node.bases) if name]
        self._visit_definition(node, "class", bases=bases)

    # ---- imports ----
    def visit_Import(self, node):
        for alias in node.names:
            if alias.asname:
                ref = ImportRef(module=alias.name, aliased=True)
                self._record_import(node, alias.name, alias.asname, ref)
            else:
                top = alias.name.split(".")[0]
                self._record_import(node, alias.name, top, ImportRef(module=top))
                # `import a.b.c` also makes the submodule reachable
                self._note_local(self.modules.to_file(alias.name, 0, self.path))

    def visit_ImportFrom(self, node):
        module = node.module or ""
        level = node.level or 0
        for alias in node.names:
            if alias.name == "*":
                continue  # can't bind names statically
            ref = ImportRef(module=module, symbol=alias.name, level=level)
            actual = f"{'.' * level}{module}.{alias.name}"
            self._record_import(node, actual, alias.asname or alias.name, ref)

    def _record_import(self, node, actual_name: str, bound_name: str, ref: ImportRef):
        self.imports.setdefault(bound_name, ref)

        target = self._import_target(ref)
        self._note_local(target)
        self.current.children.append(Node(
            type="import",
            content=self._source_span(node),
            line_number=node.lineno,
            alias=Alias(actual_name=actual_name, alias_name=bound_name,
                        local_file=bool(target), target_file=target),
        ))

    def _import_target(self, ref: ImportRef) -> Optional[str]:
        """The file an import points at. `from pkg import mod` prefers pkg/mod.py."""
        if ref.symbol:
            submodule = f"{ref.module}.{ref.symbol}" if ref.module else ref.symbol
            found = self.modules.to_file(submodule, ref.level, self.path)
            if found:
                return found
        return self.modules.to_file(ref.module, ref.level, self.path)

    def _note_local(self, file: Optional[str]):
        if file:
            self.local_imports.append(file)

    # ---- calls ----
    def visit_Call(self, node):
        name = self._call_name(node.func)
        if name:
            self.current.children.append(Node(
                type="function_call",
                content=self._source_span(node),
                line_number=node.lineno,
                end_line_number=node.end_lineno,
                function=name,
            ))
        self.generic_visit(node)


def parse_file(path: str, source: str, modules: ModuleResolver) -> SourceFile:
    """Parse `source` (the contents of repo file `path`). Raises SyntaxError on bad code."""
    tree = ast.parse(source, filename=path)
    analyzer = PyFileAnalyzer(source, path, modules)
    analyzer.visit(tree)

    defs: Dict[str, Node] = {}
    _collect_defs(analyzer.root, defs)
    return SourceFile(
        path=path,
        tree=analyzer.root,
        imports=analyzer.imports,
        defs=defs,
        local_imports=analyzer.local_imports,
    )


def _collect_defs(node: Node, defs: Dict[str, Node]):
    for child in node.children:
        if child.qualname:
            defs[child.qualname] = child
        _collect_defs(child, defs)
