"""Map import statements to files inside the repo."""
from pathlib import Path
from typing import Optional


class ModuleResolver:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def relative(self, path: Path) -> Optional[str]:
        """Repo-relative posix path, or None if `path` is outside the repo."""
        try:
            return path.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return None

    def to_file(self, dotted: str, level: int, from_file: str) -> Optional[str]:
        """The repo file an import refers to, or None for external modules.

        `level` is the number of leading dots of a relative import.
        """
        base = self._base_dir(level, from_file)
        target = base.joinpath(*dotted.split(".")) if dotted else base

        candidates = [target / "__init__.py"]
        if dotted:
            candidates.insert(0, target.parent / (target.name + ".py"))

        for candidate in candidates:
            if candidate.is_file():
                return self.relative(candidate)
        return None

    def _base_dir(self, level: int, from_file: str) -> Path:
        if level == 0:
            return self.root
        base = (self.root / from_file).parent
        for _ in range(level - 1):
            base = base.parent
        return base
