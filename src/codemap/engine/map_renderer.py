"""MapRenderer for transforming code graphs into readable Markdown.

This module provides the MapRenderer class for rendering code relationship
graphs as hierarchical Markdown documents. Each zoom level (0-4) has a
dedicated render method that combines graph traversal with Markdown formatting.

The renderer is stateless and uses GraphManager in read-only mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from codemap.graph import GraphManager


class MapRenderer:
    """Render code graph as hierarchical Markdown directory.

    Transforms a GraphManager's directed graph into human-readable Markdown
    at different zoom levels:
        - Level 0 (render_overview): Project overview with packages
        - Level 1 (render_package): Package with contained modules
        - Level 2 (render_module): Module with contained symbols
        - Level 3 (render_symbol): Symbol with signature and callers
        - Level 4 (render_code): Source code with line numbers

    The renderer is stateless and does not modify the graph.

    Example:
        >>> renderer = MapRenderer(graph_manager)
        >>> print(renderer.render_overview())
        # MyProject
        ...

        >>> renderer = MapRenderer(graph_manager, root_path=Path("."))
        >>> print(renderer.render_code("src/main.py", "main"))
    """

    def __init__(
        self,
        graph_manager: GraphManager,
        *,
        root_path: Path | None = None,
    ) -> None:
        """Initialize MapRenderer with dependencies.

        Args:
            graph_manager: GraphManager with enriched graph data.
            root_path: Project root for Level 4 code extraction.
        """
        self._graph = graph_manager
        self._root_path = root_path

    def render_overview(self) -> str:
        """Render Level 0 - Project overview.

        Finds the project node (type='project'), lists top-level packages,
        and shows architecture hints derived from inter-package imports.

        Returns:
            Markdown string with project overview.
        """
        project_id: str | None = None
        project_attrs: dict[str, Any] = {}
        for node_id, attrs in self._graph.graph.nodes(data=True):
            if attrs.get("type") == "project":
                project_id = node_id
                project_attrs = dict(attrs)
                break

        if project_id is None:
            return "# Project Overview\n\nNo project node found.\n"

        name = project_attrs.get("name", project_id)
        summary = self._get_node_summary(project_id)

        lines: list[str] = [f"# {name}", ""]
        if summary:
            lines.extend([summary, ""])

        # Top-level packages
        children = self._collect_contains_children(project_id)
        if children:
            lines.extend(["## Hauptbereiche:", ""])
            for child_id, child_attrs in children:
                child_name = child_attrs.get("name", child_id)
                child_summary = self._get_node_summary(child_id)
                if child_summary:
                    lines.append(f"- **{child_name}** - {child_summary}")
                else:
                    lines.append(f"- **{child_name}**")
            lines.append("")

        # Architecture hints from inter-package imports
        hints = self._collect_architecture_hints()
        if hints:
            lines.extend(["## Architektur-Hinweise:", ""])
            for hint in hints:
                lines.append(f"- {hint}")
            lines.append("")

        return "\n".join(lines)

    def render_package(self, package_path: str) -> str:
        """Render Level 1 - Package view.

        Args:
            package_path: Node ID of the package (e.g. 'src/auth').

        Returns:
            Markdown string with package details.

        Raises:
            ValueError: If package_path not found or not a package node.
        """
        if package_path not in self._graph.graph.nodes:
            raise ValueError(f"Package '{package_path}' not found in graph")

        attrs = dict(self._graph.graph.nodes[package_path])
        if attrs.get("type") != "package":
            raise ValueError(
                f"Node '{package_path}' is not a package (type={attrs.get('type')})"
            )

        summary = self._get_node_summary(package_path)
        risks = self._get_node_risks(package_path)

        lines: list[str] = [f"# {package_path}/", ""]
        if summary:
            lines.extend([summary, ""])

        # Contained modules / sub-packages
        children = self._collect_contains_children(package_path)
        if children:
            lines.extend(["## Module:", ""])
            for child_id, child_attrs in children:
                child_name = child_attrs.get("name", child_id)
                child_summary = self._get_node_summary(child_id)
                if child_summary:
                    lines.append(f"- **{child_name}** - {child_summary}")
                else:
                    lines.append(f"- **{child_name}**")
            lines.append("")

        # Internal structure (imports within this package)
        internal_imports = self._collect_internal_imports(package_path)
        if internal_imports:
            lines.extend(["## Interne Struktur:", ""])
            for imp in internal_imports:
                lines.append(f"- {imp}")
            lines.append("")

        # External interfaces (imports crossing package boundary)
        outgoing, incoming = self._collect_package_external_imports(package_path)
        if outgoing or incoming:
            lines.extend(["## Externe Schnittstellen:", ""])
            if outgoing:
                lines.append(f"- Importiert: {', '.join(outgoing)}")
            if incoming:
                lines.append(f"- Wird importiert von: {', '.join(incoming)}")
            lines.append("")

        # Risks
        if risks:
            lines.extend(["## Risiken:", ""])
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")

        return "\n".join(lines)

    def render_module(self, file_path: str) -> str:
        """Render Level 2 - Module view.

        Args:
            file_path: Node ID of the file (e.g. 'src/auth/login.py').

        Returns:
            Markdown string with module details.

        Raises:
            ValueError: If file_path not found or not a file node.
        """
        if file_path not in self._graph.graph.nodes:
            raise ValueError(f"Module '{file_path}' not found in graph")

        attrs = dict(self._graph.graph.nodes[file_path])
        if attrs.get("type") != "file":
            raise ValueError(
                f"Node '{file_path}' is not a file (type={attrs.get('type')})"
            )

        summary = self._get_node_summary(file_path)
        risks = self._get_node_risks(file_path)

        lines: list[str] = [f"# {file_path}", ""]
        if summary:
            lines.extend([summary, ""])

        # Contained symbols (functions, classes)
        children = self._collect_contains_children(file_path)
        if children:
            lines.extend(["## Enthält:", ""])
            for child_id, child_attrs in children:
                child_name = child_attrs.get("name", child_id)
                child_summary = self._get_node_summary(child_id)
                if child_summary:
                    lines.append(f"- **{child_name}** - {child_summary}")
                else:
                    lines.append(f"- **{child_name}**")
            lines.append("")

        # Dependencies
        outgoing, incoming = self._collect_imports(file_path)
        if outgoing or incoming:
            lines.extend(["## Abhängigkeiten:", ""])
            if outgoing:
                lines.append(f"- Importiert: {', '.join(outgoing)}")
            if incoming:
                # Count imports per source
                import_counts: dict[str, int] = {}
                for src in incoming:
                    import_counts[src] = import_counts.get(src, 0) + 1
                formatted = [
                    f"{src} ({count}x)" for src, count in import_counts.items()
                ]
                lines.append(f"- Wird importiert von: {', '.join(formatted)}")
            lines.append("")

        # Risks
        if risks:
            lines.extend(["## Risiken:", ""])
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")

        return "\n".join(lines)

    def render_symbol(self, file_path: str, symbol_name: str) -> str:
        """Render Level 3 - Symbol view.

        Args:
            file_path: Parent file path (e.g. 'src/auth/login.py').
            symbol_name: Symbol name (e.g. 'authenticate').

        Returns:
            Markdown string with symbol details.

        Raises:
            ValueError: If symbol not found in graph.
        """
        node_id = f"{file_path}::{symbol_name}"
        if node_id not in self._graph.graph.nodes:
            raise ValueError(f"Symbol '{node_id}' not found in graph")

        attrs = dict(self._graph.graph.nodes[node_id])
        summary = self._get_node_summary(node_id)
        risks = self._get_node_risks(node_id)
        node_type = attrs.get("type", "unknown")

        lines: list[str] = [f"# {node_id}", ""]

        # Signature
        if node_type == "function":
            lines.extend(["## Signatur:", "", f"def {symbol_name}(...)", ""])
        elif node_type == "class":
            lines.extend(["## Signatur:", "", f"class {symbol_name}:", ""])

        # Behavior (summary)
        if summary:
            lines.extend(["## Verhalten:", "", summary, ""])

        # Callers (files importing the parent file)
        callers = self._find_callers(file_path)
        if callers:
            lines.extend(["## Aufrufer:", ""])
            for caller in callers:
                lines.append(f"- {caller}")
            lines.append("")

        # Risks
        if risks:
            lines.extend(["## Risiken:", ""])
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")

        return "\n".join(lines)

    def render_code(self, file_path: str, symbol_name: str) -> str:
        """Render Level 4 - Source code with line numbers.

        Args:
            file_path: Parent file path (e.g. 'src/auth/login.py').
            symbol_name: Symbol name (e.g. 'authenticate').

        Returns:
            Markdown string with source code block and line numbers.

        Raises:
            ValueError: If root_path not set, symbol not found,
                file not found, or invalid line range.
        """
        if self._root_path is None:
            raise ValueError("root_path is required for code extraction")

        node_id = f"{file_path}::{symbol_name}"
        if node_id not in self._graph.graph.nodes:
            raise ValueError(f"Symbol '{node_id}' not found in graph")

        attrs = dict(self._graph.graph.nodes[node_id])
        start_line = attrs.get("start_line")
        end_line = attrs.get("end_line")

        if start_line is None or end_line is None:
            raise ValueError(f"Symbol '{node_id}' has no line range")

        if start_line > end_line:
            raise ValueError(
                f"Invalid line range for '{node_id}': {start_line}-{end_line}"
            )

        abs_path = self._root_path / file_path
        try:
            content = abs_path.read_text()
        except FileNotFoundError:
            raise ValueError(f"File not found: {abs_path}") from None

        all_lines = content.splitlines()
        code_lines = all_lines[start_line - 1 : end_line]

        # Format with line numbers
        numbered: list[str] = []
        for i, line in enumerate(code_lines, start=start_line):
            numbered.append(f"{i:4d} | {line}")

        ext = Path(file_path).suffix.lstrip(".")
        lang_map: dict[str, str] = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
        }
        lang = lang_map.get(ext, ext)

        result_lines: list[str] = [
            f"# {node_id} - Quellcode",
            "",
            f"```{lang}",
            *numbered,
            "```",
            "",
            f"Zeilen {start_line}-{end_line}",
        ]

        return "\n".join(result_lines)

    # --- Private helpers ---

    def _get_node_summary(self, node_id: str) -> str:
        """Extract summary attribute or return empty string."""
        if node_id not in self._graph.graph.nodes:
            return ""
        return str(self._graph.graph.nodes[node_id].get("summary", ""))

    def _get_node_risks(self, node_id: str) -> list[str]:
        """Extract risks attribute or return empty list."""
        if node_id not in self._graph.graph.nodes:
            return []
        risks = self._graph.graph.nodes[node_id].get("risks", [])
        if isinstance(risks, list):
            return [str(r) for r in risks]
        return []

    def _collect_contains_children(
        self, node_id: str
    ) -> list[tuple[str, dict[str, Any]]]:
        """Collect all CONTAINS children with their attributes."""
        children: list[tuple[str, dict[str, Any]]] = []
        for _, target, data in self._graph.graph.out_edges(node_id, data=True):
            if data.get("relationship") == "CONTAINS":
                children.append((target, dict(self._graph.graph.nodes[target])))
        return children

    def _collect_imports(self, node_id: str) -> tuple[list[str], list[str]]:
        """Collect outgoing and incoming IMPORTS edges for a node."""
        outgoing: list[str] = []
        incoming: list[str] = []
        for _, target, data in self._graph.graph.out_edges(node_id, data=True):
            if data.get("relationship") == "IMPORTS":
                outgoing.append(target)
        for source, _, data in self._graph.graph.in_edges(node_id, data=True):
            if data.get("relationship") == "IMPORTS":
                incoming.append(source)
        return outgoing, incoming

    def _get_parent_package(self, node_id: str) -> str | None:
        """Determine the parent package path for a node.

        For file nodes, returns the directory. For code nodes (with '::'),
        first extracts the file path, then returns its directory.
        """
        if "::" in node_id:
            node_id = node_id.split("::")[0]
        path = Path(node_id)
        if len(path.parts) > 1:
            return str(Path(*path.parts[:-1]))
        return None

    def _collect_architecture_hints(self) -> list[str]:
        """Collect inter-package import relationships for architecture view."""
        package_imports: set[tuple[str, str]] = set()
        for source, target, data in self._graph.graph.edges(data=True):
            if data.get("relationship") != "IMPORTS":
                continue
            source_pkg = self._get_parent_package(source)
            target_pkg = self._get_parent_package(target)
            if source_pkg and target_pkg and source_pkg != target_pkg:
                package_imports.add((source_pkg, target_pkg))
        return [f"{src} importiert {tgt}" for src, tgt in sorted(package_imports)]

    def _collect_internal_imports(self, package_id: str) -> list[str]:
        """Collect import relationships between modules within a package."""
        internal: list[str] = []
        children = self._collect_contains_children(package_id)
        child_ids = {cid for cid, _ in children}

        for child_id in child_ids:
            for _, target, data in self._graph.graph.out_edges(child_id, data=True):
                if data.get("relationship") == "IMPORTS" and target in child_ids:
                    source_name = Path(child_id).name
                    target_name = Path(target).name
                    internal.append(f"{source_name} importiert {target_name}")

        return internal

    def _collect_package_external_imports(
        self, package_id: str
    ) -> tuple[list[str], list[str]]:
        """Collect imports crossing the package boundary."""
        outgoing: list[str] = []
        incoming: list[str] = []
        children = self._collect_contains_children(package_id)
        child_ids = {cid for cid, _ in children}

        for child_id in child_ids:
            for _, target, data in self._graph.graph.out_edges(child_id, data=True):
                if data.get("relationship") == "IMPORTS" and target not in child_ids:
                    if target not in outgoing:
                        outgoing.append(target)
            for source, _, data in self._graph.graph.in_edges(child_id, data=True):
                if data.get("relationship") == "IMPORTS" and source not in child_ids:
                    if source not in incoming:
                        incoming.append(source)

        return outgoing, incoming

    def _find_callers(self, file_path: str) -> list[str]:
        """Find files that import the given file (potential callers)."""
        callers: list[str] = []
        for source, _, data in self._graph.graph.in_edges(file_path, data=True):
            if data.get("relationship") == "IMPORTS":
                callers.append(source)
        return callers
