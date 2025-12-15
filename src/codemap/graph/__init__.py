"""Graph module for building knowledge graphs of code relationships.

This module provides tools to build and persist directed graphs representing
code relationships using NetworkX.

Node Types:
    - file: Represents a source file in the project (type="file")
    - code element: Represents classes/functions within files (type="class"/"function")
    - external_module: Represents external dependencies like stdlib or third-party
      packages (type="external_module")

Edge Types:
    - CONTAINS: From file node to code element nodes within that file
    - IMPORTS: From file node to imported target. The target can be another file
      node (internal import) or an external_module node (stdlib/third-party import)

Distinguishing Internal vs External Imports:
    All IMPORTS edges use the same relationship="IMPORTS" attribute regardless of
    whether the import is internal or external. There is no separate edge type or
    attribute for external imports.

    To determine if an import is external, check the target node's type attribute:
        - type="file" -> internal project import
        - type="external_module" -> external import (stdlib/third-party)

    This design keeps the edge semantics simple (source imports target) while the
    node type carries the semantic meaning of what kind of module is being imported.

External modules are created lazily by add_dependency() when the target doesn't
exist, allowing the caller to enrich them with type="external_module" afterward.
"""

from codemap.graph.manager import GraphManager

__all__ = [
    "GraphManager",
]
