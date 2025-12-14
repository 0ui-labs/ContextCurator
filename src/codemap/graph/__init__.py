"""Graph module for building knowledge graphs of code relationships.

This module provides tools to build and persist directed graphs representing
code relationships using NetworkX. Nodes represent files and code elements
(classes, functions), while edges represent relationships (CONTAINS, IMPORTS).
"""

from codemap.graph.manager import GraphManager

__all__ = [
    "GraphManager",
]
