"""Static call-graph extraction for Python repos.

Pipeline: parser (file -> Node tree) -> resolver (calls -> definitions) -> output.
"""
from .analyzer import build_graph

__all__ = ["build_graph"]
