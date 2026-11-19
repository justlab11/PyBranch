"""Stage 2: link each call to the definition it refers to."""
from typing import Dict, List, Optional, Set, Tuple

from .models import Edge, ImportRef, Node, SourceFile, make_ref, split_ref
from .modules import ModuleResolver

MAX_IMPORT_DEPTH = 5  # how many re-exports (`from .x import y`) we follow


class CallResolver:
    def __init__(self, files: Dict[str, SourceFile], modules: ModuleResolver):
        self.files = files
        self.modules = modules

    # ---- entry point ----
    def resolve_all(self) -> List[Edge]:
        edges: List[Edge] = []

        for path, source in self.files.items():
            self._walk(path, source.tree, [], edges)

        return edges

    def _walk(self, path: str, node: Node, scope: List[Node], edges: List[Edge]):
        """`scope` is the chain of enclosing function/class nodes."""
        for child in node.children:
            if child.type == "function_call" and child.function:
                child.resolved = self._resolve_call(path, child.function, scope)

                if child.resolved:
                    edges.append(Edge(
                        source=make_ref(path, self._enclosing_function(scope)),
                        target=child.resolved,
                        line=child.line_number,
                    ))

            inner = scope + [child] if child.qualname else scope
            self._walk(path, child, inner, edges)

    @staticmethod
    def _enclosing_function(scope: List[Node]) -> str:
        for node in reversed(scope):
            if node.type == "function":
                return node.qualname or "<module>"
            
        return "<module>"

    @staticmethod
    def _enclosing_class(scope: List[Node]) -> Optional[Node]:
        return next((n for n in reversed(scope) if n.type == "class"), None)

    # ---- a single call ----
    def _resolve_call(self, path: str, name: str, scope: List[Node]) -> Optional[str]:
        parts = name.split(".")
        head = parts[0]

        if head.startswith("<"):  # call on an arbitrary expression
            return None
        
        if head in ("self", "cls", "super"):
            return self._resolve_instance_call(path, parts, scope)

        return self._resolve_nested(path, parts, scope) or self.lookup(path, parts)

    def _resolve_instance_call(self, path: str, parts: List[str], scope: List[Node]) -> Optional[str]:
        """self.method(), cls.method(), super().method()"""
        cls = self._enclosing_class(scope)

        if cls is None or len(parts) != 2:
            return None
        
        head, method = parts
        if head == "super":
            return self._find_in_bases(path, cls, method)
        return self.find_method(path, cls.qualname or "", method)

    def _resolve_nested(self, path: str, parts: List[str], scope: List[Node]) -> Optional[str]:
        """A function defined inside an enclosing function shadows module-level names."""
        for node in reversed(scope):
            if node.type != "function":
                continue

            prefix = node.qualname or ""
            found = self._definition(path, prefix.split(".") + parts)

            if found and split_ref(found)[1].startswith(prefix + "."):
                return found
            
        return None

    # ---- symbol lookup ----
    def _definition(self, path: str, parts: List[str], ctor: bool = True) -> Optional[str]:
        """Exact match of a dotted name against a file's definitions.

        With `ctor`, a class resolves to its __init__ (what actually runs on a call).
        """
        defs = self.files[path].defs if path in self.files else {}
        qualname = ".".join(parts)
        definition = defs.get(qualname)

        if definition is None:
            return None
        
        if ctor and definition.type == "class" and f"{qualname}.__init__" in defs:
            qualname += ".__init__"

        return make_ref(path, qualname)

    def lookup(self, path: str, parts: List[str], depth: int = 0, ctor: bool = True) -> Optional[str]:
        """Resolve a dotted name used in `path`: local definitions first, then imports."""
        found = self._definition(path, parts, ctor)
        if found or depth > MAX_IMPORT_DEPTH:
            return found

        ref = self.files[path].imports.get(parts[0])
        if ref is None:
            return None
        
        return self._follow_import(path, ref, parts[1:], depth, ctor)

    def _follow_import(self, path: str, ref: ImportRef, rest: List[str], depth: int, ctor: bool):
        module = self._bound_module(path, ref)
        if module is not None:
            return self._lookup_in_module(path, module, ref.level, rest, depth, ctor)

        target = self.modules.to_file(ref.module, ref.level, path)
        if target in self.files:
            return self.lookup(target, [ref.symbol or ""] + rest, depth + 1, ctor)
        
        return None

    def _bound_module(self, path: str, ref: ImportRef) -> Optional[str]:
        """Dotted module name if the import binds a module, None if it binds a symbol."""
        if ref.symbol is None:
            return ref.module
        
        full = f"{ref.module}.{ref.symbol}" if ref.module else ref.symbol
        return full if self.modules.to_file(full, ref.level, path) else None

    def _lookup_in_module(self, path: str, module: str, level: int, rest: List[str],
                          depth: int, ctor: bool) -> Optional[str]:
        # `pkg.sub.func()`: absorb leading parts that are submodules
        rest = list(rest)
        while rest and self.modules.to_file(f"{module}.{rest[0]}", level, path):
            module += "." + rest.pop(0)

        target = self.modules.to_file(module, level, path)
        if not target or not rest or target not in self.files:
            return None
        return self.lookup(target, rest, depth + 1, ctor)

    # ---- inheritance ----
    def find_method(self, path: str, class_qualname: str, method: str,
                    seen: Optional[Set[Tuple[str, str]]] = None) -> Optional[str]:
        """`method` on the class, or on the first base class that defines it."""
        seen = set() if seen is None else seen
        if (path, class_qualname) in seen:
            return None
        seen.add((path, class_qualname))

        found = self._definition(path, class_qualname.split(".") + [method])
        if found:
            return found
        cls = self.files[path].defs.get(class_qualname)
        return self._find_in_bases(path, cls, method, seen) if cls else None

    def _find_in_bases(self, path: str, cls: Node, method: str,
                       seen: Optional[Set[Tuple[str, str]]] = None) -> Optional[str]:
        for base in cls.bases:
            base_ref = self.lookup(path, base.split("."), ctor=False)
            if not base_ref:
                continue
            base_path, base_qualname = split_ref(base_ref)
            found = self.find_method(base_path, base_qualname, method, seen)
            if found:
                return found
        return None
