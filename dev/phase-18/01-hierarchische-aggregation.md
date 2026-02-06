# Phase 18: Hierarchische Aggregation

> **Ziel:** Zoom-Level Struktur aufbauen (Projekt → Package → Modul → Funktion).
> Der Graph bekommt eine hierarchische Struktur, die Navigation von "weit weg" bis "ganz nah" ermöglicht.

---

## Problem

Aktuell ist der Graph flach strukturiert:

```
file_node → code_node (function/class)
file_node → file_node (IMPORTS)
```

Es fehlt die Möglichkeit, "rauszuzoomen":
- Was macht das `auth`-Package insgesamt?
- Was sind die Hauptkomponenten des Projekts?
- Welche Packages hängen voneinander ab?

## Lösung

Hierarchische Struktur mit 5 Zoom-Levels:

```
Level 0: Projekt-Root        "ContextCurator - Code-Mapping Tool"
    │
Level 1: Package/Directory   "auth/ - Authentifizierung & Session-Management"
    │                        "api/ - REST-Endpoints für externe Clients"
    │
Level 2: Modul/Datei         "auth/login.py - Login-Flow mit JWT"
    │
Level 3: Klasse/Funktion     "authenticate_user() - Validiert Credentials"
    │
Level 4: Code-Detail         (Raw Source - bereits via Phase 17)
```

---

## Observations

Nach Analyse des bestehenden Codes:

- **GraphManager hat flache Struktur:** Nur `file`, `function`, `class`, `external_module` Node-Types
- **CONTAINS-Edges existieren:** `file → code_node`, aber keine `package → file`
- **Keine Package-Nodes:** Verzeichnisstruktur wird nicht im Graph abgebildet
- **Summaries auf Code-Level:** GraphEnricher enriched nur `function`/`class` Nodes
- **Node-IDs sind Pfade:** `src/auth/login.py::authenticate_user` - Hierarchie ist implizit

## Approach

### 1. Package-Nodes einführen (GraphManager erweitern)

Neue Node-Types:
- `project` (Level 0): Genau einer pro Graph
- `package` (Level 1): Ein Node pro Verzeichnis mit Python-Dateien

Neue Methoden in GraphManager:
```python
def add_package(self, package_path: str) -> None:
    """Fügt Package-Node hinzu mit CONTAINS-Edge zum Parent."""

def add_project(self, name: str) -> None:
    """Fügt Project-Root-Node hinzu."""

def build_hierarchy(self) -> None:
    """Erstellt Package-Nodes aus bestehenden File-Nodes."""
```

### 2. Level-Attribut auf allen Nodes

```python
# Beispiel Node-Attribute nach Hierarchie-Build
{
    "id": "src/auth",
    "type": "package",
    "level": 1,
    "name": "auth",
    "children_count": 3,  # Anzahl direkter Kinder
}
```

### 3. Aggregations-Enricher (neuer HierarchyEnricher)

Neuer Enricher für Bottom-Up Summary-Aggregation:
```python
class HierarchyEnricher:
    """Aggregiert Summaries von unten nach oben."""

    async def aggregate_summaries(self) -> None:
        """
        1. Sammle alle Summaries der Kinder eines Package-Nodes
        2. Sende an LLM: "Fasse diese Modul-Summaries zusammen"
        3. Speichere aggregierte Summary auf Package-Node
        4. Wiederhole für nächsthöheres Level
        """
```

---

## Implementation Steps

### Phase 1: RED - Failing Tests schreiben

#### 1.1 GraphManager Tests erweitern

Datei: `tests/unit/graph/test_manager.py`

```python
class TestHierarchyBuilding:
    """Tests for hierarchical graph structure."""

    def test_add_project_creates_root_node(self, manager: GraphManager) -> None:
        """add_project() creates a level-0 project node."""
        manager.add_project("MyProject")

        assert "project::MyProject" in manager.graph.nodes
        node = manager.graph.nodes["project::MyProject"]
        assert node["type"] == "project"
        assert node["level"] == 0
        assert node["name"] == "MyProject"

    def test_add_package_creates_package_node(self, manager: GraphManager) -> None:
        """add_package() creates a level-1 package node."""
        manager.add_project("MyProject")
        manager.add_package("src/auth")

        assert "src/auth" in manager.graph.nodes
        node = manager.graph.nodes["src/auth"]
        assert node["type"] == "package"
        assert node["level"] == 1
        assert node["name"] == "auth"

    def test_add_package_creates_contains_edge_to_project(
        self, manager: GraphManager
    ) -> None:
        """Package at root level gets CONTAINS edge from project."""
        manager.add_project("MyProject")
        manager.add_package("src")

        assert manager.graph.has_edge("project::MyProject", "src")
        edge = manager.graph.edges["project::MyProject", "src"]
        assert edge["relationship"] == "CONTAINS"

    def test_nested_package_creates_contains_edge_to_parent(
        self, manager: GraphManager
    ) -> None:
        """Nested package gets CONTAINS edge from parent package."""
        manager.add_project("MyProject")
        manager.add_package("src")
        manager.add_package("src/auth")

        assert manager.graph.has_edge("src", "src/auth")
        edge = manager.graph.edges["src", "src/auth"]
        assert edge["relationship"] == "CONTAINS"

    def test_add_package_calculates_correct_level(
        self, manager: GraphManager
    ) -> None:
        """Package level equals directory depth."""
        manager.add_project("MyProject")
        manager.add_package("src")           # level 1
        manager.add_package("src/auth")      # level 2
        manager.add_package("src/auth/oauth") # level 3

        assert manager.graph.nodes["src"]["level"] == 1
        assert manager.graph.nodes["src/auth"]["level"] == 2
        assert manager.graph.nodes["src/auth/oauth"]["level"] == 3

    def test_build_hierarchy_creates_packages_from_files(
        self, manager: GraphManager
    ) -> None:
        """build_hierarchy() infers packages from existing file nodes."""
        # Setup: Add files without packages
        manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/auth/session.py"), 100, 25))
        manager.add_file(FileEntry(Path("src/api/routes.py"), 100, 25))

        manager.build_hierarchy("MyProject")

        # Verify packages were created
        assert "project::MyProject" in manager.graph.nodes
        assert "src" in manager.graph.nodes
        assert "src/auth" in manager.graph.nodes
        assert "src/api" in manager.graph.nodes

        # Verify hierarchy edges
        assert manager.graph.has_edge("project::MyProject", "src")
        assert manager.graph.has_edge("src", "src/auth")
        assert manager.graph.has_edge("src", "src/api")
        assert manager.graph.has_edge("src/auth", "src/auth/login.py")

    def test_file_nodes_get_level_attribute(self, manager: GraphManager) -> None:
        """File nodes receive level attribute based on depth."""
        manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        manager.build_hierarchy("MyProject")

        file_node = manager.graph.nodes["src/auth/login.py"]
        assert file_node["level"] == 3  # src(1) / auth(2) / file(3)

    def test_code_nodes_get_level_attribute(self, manager: GraphManager) -> None:
        """Code nodes (function/class) receive level = file_level + 1."""
        manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
        manager.add_node("src/auth/login.py", CodeNode("function", "login", 1, 10))
        manager.build_hierarchy("MyProject")

        code_node = manager.graph.nodes["src/auth/login.py::login"]
        assert code_node["level"] == 4  # file is level 3, code is level 4
```

#### 1.2 HierarchyEnricher Tests

Neue Datei: `tests/unit/engine/test_hierarchy_enricher.py`

```python
"""Tests for HierarchyEnricher."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from codemap.engine.hierarchy_enricher import HierarchyEnricher
from codemap.graph import GraphManager
from codemap.core.llm import LLMProvider


@pytest.fixture
def graph_with_hierarchy() -> GraphManager:
    """Create a graph with hierarchical structure and summaries."""
    manager = GraphManager()

    # Build structure: project -> src -> auth -> login.py -> func
    manager.add_file(FileEntry(Path("src/auth/login.py"), 100, 25))
    manager.add_node("src/auth/login.py", CodeNode("function", "authenticate", 1, 10))
    manager.add_node("src/auth/login.py", CodeNode("function", "logout", 11, 20))
    manager.build_hierarchy("TestProject")

    # Add summaries to leaf nodes (simulating GraphEnricher output)
    manager.graph.nodes["src/auth/login.py::authenticate"]["summary"] = (
        "Validates user credentials and returns JWT token"
    )
    manager.graph.nodes["src/auth/login.py::logout"]["summary"] = (
        "Invalidates session and clears auth cookies"
    )

    return manager


class TestHierarchyEnricherInit:
    """Tests for HierarchyEnricher initialization."""

    def test_init_with_graph_and_provider(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """HierarchyEnricher accepts GraphManager and LLMProvider."""
        provider = MagicMock(spec=LLMProvider)
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)

        assert enricher._graph_manager is graph_with_hierarchy
        assert enricher._llm_provider is provider


class TestAggregationBottomUp:
    """Tests for bottom-up summary aggregation."""

    @pytest.mark.asyncio
    async def test_aggregate_file_summary_from_code_nodes(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """File summary is aggregated from its code node summaries."""
        provider = AsyncMock(spec=LLMProvider)
        provider.send.return_value = (
            '[{"node_id": "src/auth/login.py", '
            '"summary": "Authentication module with login and logout functionality"}]'
        )

        enricher = HierarchyEnricher(graph_with_hierarchy, provider)
        await enricher.aggregate_summaries()

        file_node = graph_with_hierarchy.graph.nodes["src/auth/login.py"]
        assert "summary" in file_node
        assert "Authentication" in file_node["summary"]

    @pytest.mark.asyncio
    async def test_aggregate_package_summary_from_file_nodes(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Package summary is aggregated from its file summaries."""
        provider = AsyncMock(spec=LLMProvider)
        # First call: aggregate file from code nodes
        # Second call: aggregate package from files
        provider.send.side_effect = [
            '[{"node_id": "src/auth/login.py", "summary": "Auth module"}]',
            '[{"node_id": "src/auth", "summary": "Authentication package"}]',
        ]

        enricher = HierarchyEnricher(graph_with_hierarchy, provider)
        await enricher.aggregate_summaries()

        package_node = graph_with_hierarchy.graph.nodes["src/auth"]
        assert "summary" in package_node

    @pytest.mark.asyncio
    async def test_aggregation_processes_levels_bottom_to_top(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Aggregation processes level 3 before level 2 before level 1."""
        provider = AsyncMock(spec=LLMProvider)
        call_order = []

        async def track_calls(system: str, user: str) -> str:
            # Extract which nodes are being aggregated from prompt
            if "src/auth/login.py::" in user:
                call_order.append("level_3_to_file")
            elif "src/auth/login.py" in user and "::" not in user:
                call_order.append("level_2_to_package")
            return '[{"node_id": "dummy", "summary": "test"}]'

        provider.send.side_effect = track_calls

        enricher = HierarchyEnricher(graph_with_hierarchy, provider)
        await enricher.aggregate_summaries()

        # Level 3 (code→file) should be processed before level 2 (file→package)
        assert call_order.index("level_3_to_file") < call_order.index("level_2_to_package")

    @pytest.mark.asyncio
    async def test_skips_nodes_without_children_summaries(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Nodes are skipped if children don't have summaries yet."""
        # Remove summaries from code nodes
        del graph_with_hierarchy.graph.nodes["src/auth/login.py::authenticate"]["summary"]
        del graph_with_hierarchy.graph.nodes["src/auth/login.py::logout"]["summary"]

        provider = AsyncMock(spec=LLMProvider)
        enricher = HierarchyEnricher(graph_with_hierarchy, provider)
        await enricher.aggregate_summaries()

        # File should not have summary (no children with summaries)
        assert "summary" not in graph_with_hierarchy.graph.nodes["src/auth/login.py"]
        # LLM should not have been called
        provider.send.assert_not_called()


class TestProjectLevelAggregation:
    """Tests for project-level (level 0) aggregation."""

    @pytest.mark.asyncio
    async def test_project_summary_aggregates_top_packages(
        self, graph_with_hierarchy: GraphManager
    ) -> None:
        """Project summary is aggregated from top-level package summaries."""
        # Add summaries to all levels
        graph_with_hierarchy.graph.nodes["src/auth/login.py"]["summary"] = "Auth file"
        graph_with_hierarchy.graph.nodes["src/auth"]["summary"] = "Auth package"
        graph_with_hierarchy.graph.nodes["src"]["summary"] = "Source root"

        provider = AsyncMock(spec=LLMProvider)
        provider.send.return_value = (
            '[{"node_id": "project::TestProject", '
            '"summary": "Code mapping and analysis tool"}]'
        )

        enricher = HierarchyEnricher(graph_with_hierarchy, provider)
        await enricher.aggregate_summaries()

        project_node = graph_with_hierarchy.graph.nodes["project::TestProject"]
        assert "summary" in project_node
```

---

### Phase 2: GREEN - Implementation

#### 2.1 GraphManager erweitern

Datei: `src/codemap/graph/manager.py`

Neue Methoden:
```python
def add_project(self, name: str) -> None:
    """Add project root node (level 0).

    Args:
        name: Project name for display.
    """
    node_id = f"project::{name}"
    self._graph.add_node(
        node_id,
        type="project",
        level=0,
        name=name,
    )

def add_package(self, package_path: str, project_id: str | None = None) -> None:
    """Add package node with correct level and parent edge.

    Args:
        package_path: Relative path like "src/auth".
        project_id: Project node ID for root-level packages.
    """
    parts = Path(package_path).parts
    level = len(parts)
    name = parts[-1] if parts else package_path

    self._graph.add_node(
        package_path,
        type="package",
        level=level,
        name=name,
    )

    # Connect to parent
    if len(parts) > 1:
        parent_path = str(Path(*parts[:-1]))
        self._graph.add_edge(parent_path, package_path, relationship="CONTAINS")
    elif project_id:
        self._graph.add_edge(project_id, package_path, relationship="CONTAINS")

def build_hierarchy(self, project_name: str) -> None:
    """Build hierarchical structure from existing file nodes.

    Creates project and package nodes, sets level attributes,
    and establishes CONTAINS edges.

    Args:
        project_name: Name for the project root node.
    """
    # 1. Create project node
    project_id = f"project::{project_name}"
    self.add_project(project_name)

    # 2. Collect all unique directory paths from files
    directories: set[str] = set()
    for node_id, attrs in self._graph.nodes(data=True):
        if attrs.get("type") == "file":
            path = Path(node_id)
            # Add all parent directories
            for i in range(1, len(path.parts)):
                directories.add(str(Path(*path.parts[:i])))

    # 3. Create package nodes (sorted by depth for proper parent creation)
    for dir_path in sorted(directories, key=lambda p: len(Path(p).parts)):
        self.add_package(dir_path, project_id)

    # 4. Update file nodes with level and connect to parent package
    for node_id, attrs in list(self._graph.nodes(data=True)):
        if attrs.get("type") == "file":
            path = Path(node_id)
            file_level = len(path.parts)
            self._graph.nodes[node_id]["level"] = file_level

            # Connect file to parent package
            if len(path.parts) > 1:
                parent_dir = str(Path(*path.parts[:-1]))
                if parent_dir in self._graph.nodes:
                    # Remove old edge if exists, add new one
                    self._graph.add_edge(parent_dir, node_id, relationship="CONTAINS")
            else:
                # Root-level file connects to project
                self._graph.add_edge(project_id, node_id, relationship="CONTAINS")

    # 5. Update code nodes with level
    for node_id, attrs in self._graph.nodes(data=True):
        if attrs.get("type") in ("function", "class"):
            # Code node level = parent file level + 1
            file_id = node_id.split("::")[0]
            if file_id in self._graph.nodes:
                file_level = self._graph.nodes[file_id].get("level", 0)
                self._graph.nodes[node_id]["level"] = file_level + 1
```

#### 2.2 HierarchyEnricher erstellen

Neue Datei: `src/codemap/engine/hierarchy_enricher.py`

```python
"""HierarchyEnricher for bottom-up summary aggregation.

This module provides the HierarchyEnricher class for aggregating
summaries from child nodes to parent nodes in a hierarchical graph.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any

import orjson

from codemap.core.llm import LLMProvider
from codemap.graph import GraphManager

logger = logging.getLogger(__name__)


class HierarchyEnricher:
    """Aggregate summaries bottom-up through the graph hierarchy.

    This class processes the graph level by level, starting from
    the deepest level (code nodes) and working up to the project root.
    At each level, it collects child summaries and asks the LLM to
    create an aggregated summary.

    Architecture:
        - Processes levels in descending order (4 → 3 → 2 → 1 → 0)
        - Uses asyncio.gather for parallel processing within a level
        - Skips nodes whose children don't have summaries
        - Updates graph nodes with aggregated "summary" attribute

    Example:
        enricher = HierarchyEnricher(graph_manager, llm_provider)
        await enricher.aggregate_summaries()
    """

    def __init__(
        self,
        graph_manager: GraphManager,
        llm_provider: LLMProvider,
    ) -> None:
        """Initialize HierarchyEnricher with dependencies."""
        self._graph_manager = graph_manager
        self._llm_provider = llm_provider

    async def aggregate_summaries(self) -> None:
        """Aggregate summaries from bottom to top.

        Process:
            1. Group nodes by level
            2. For each level (highest to lowest):
               - Find nodes that have children with summaries
               - Call LLM to aggregate child summaries
               - Update parent node with aggregated summary
        """
        # Group nodes by level
        nodes_by_level: dict[int, list[str]] = defaultdict(list)
        for node_id, attrs in self._graph_manager.graph.nodes(data=True):
            level = attrs.get("level")
            if level is not None:
                nodes_by_level[level].append(node_id)

        if not nodes_by_level:
            logger.info("No nodes with level attribute found")
            return

        # Process from second-highest level down to 0
        # (highest level nodes are leaves, they already have summaries)
        max_level = max(nodes_by_level.keys())

        for level in range(max_level - 1, -1, -1):
            parent_nodes = nodes_by_level.get(level, [])
            if not parent_nodes:
                continue

            tasks = [
                self._aggregate_node(node_id)
                for node_id in parent_nodes
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _aggregate_node(self, node_id: str) -> None:
        """Aggregate summaries for a single parent node."""
        # Find children (nodes connected via CONTAINS edge)
        children_summaries: list[tuple[str, str]] = []

        for _, child_id, edge_data in self._graph_manager.graph.out_edges(node_id, data=True):
            if edge_data.get("relationship") != "CONTAINS":
                continue

            child_attrs = self._graph_manager.graph.nodes[child_id]
            summary = child_attrs.get("summary")
            if summary:
                child_name = child_attrs.get("name", child_id)
                children_summaries.append((child_name, summary))

        if not children_summaries:
            logger.debug(f"No children with summaries for {node_id}")
            return

        # Build prompt
        node_attrs = self._graph_manager.graph.nodes[node_id]
        node_type = node_attrs.get("type", "unknown")
        node_name = node_attrs.get("name", node_id)

        system_prompt = (
            "You are a code analysis assistant. Summarize the following "
            "child components into a single cohesive summary for the parent. "
            "Return JSON: [{\"node_id\": \"...\", \"summary\": \"...\"}]"
        )

        child_lines = [
            f"- {name}: {summary}"
            for name, summary in children_summaries
        ]

        user_prompt = (
            f"Summarize these components of {node_type} '{node_name}':\n\n"
            + "\n".join(child_lines)
            + f"\n\nReturn summary for node_id: {node_id}"
        )

        try:
            response = await self._llm_provider.send(system_prompt, user_prompt)
            results = orjson.loads(response)

            for result in results:
                if result.get("node_id") == node_id:
                    self._graph_manager.graph.nodes[node_id]["summary"] = result.get("summary", "")
                    break

        except Exception as e:
            logger.warning(f"Failed to aggregate summary for {node_id}: {e}")
```

---

### Phase 3: REFACTOR - Code-Qualität verbessern

#### 3.1 Checklist

- [ ] mypy strict auf neuen Dateien
- [ ] ruff Format und Lint
- [ ] Docstrings vollständig
- [ ] Edge-Cases abgedeckt (leere Packages, einzelne Dateien)
- [ ] Integration mit MapBuilder (optional: `build_hierarchy` automatisch aufrufen)

#### 3.2 Performance-Betrachtung

- Parallelisierung innerhalb eines Levels
- Batch-Processing für LLM-Calls (wie in GraphEnricher)
- Caching von Zwischenergebnissen

---

## Akzeptanzkriterien

- [ ] `GraphManager.build_hierarchy()` erstellt Package-Nodes aus File-Nodes
- [ ] Alle Nodes haben `level`-Attribut (0-4)
- [ ] CONTAINS-Edges bilden Hierarchie: project → package → file → code
- [ ] `HierarchyEnricher.aggregate_summaries()` aggregiert bottom-up
- [ ] Package-Summaries fassen Kind-Summaries zusammen
- [ ] 100% Test-Coverage bleibt erhalten
- [ ] mypy strict + ruff clean

---

## Abhängigkeiten

- **Phase 17 (Code-Content Integration):** Muss abgeschlossen sein, damit Code-Nodes Summaries haben
- **GraphEnricher:** Muss zuerst laufen, damit Leaf-Nodes Summaries bekommen

## Risiken

1. **Token-Explosion bei großen Packages:** Viele Kind-Summaries → zu langer Prompt
   - Mitigation: Batching oder Zwischenaggregation

2. **Zirkuläre Dependencies:** Package A importiert aus Package B und umgekehrt
   - Mitigation: IMPORTS-Edges sind separate Hierarchie, nicht in CONTAINS

3. **Inkonsistente Hierarchie nach inkrementellem Update:**
   - Mitigation: Phase 19 behandelt das explizit

---

## Schätzung

- **Aufwand:** 🔴 Hoch (wie in Roadmap angegeben)
- **Komplexität:** GraphManager-Erweiterung + neuer Enricher + Bottom-Up-Logik
- **Zeitrahmen:** 2-3 TDD-Zyklen (RED → GREEN → REFACTOR)

---

## Nächster Schritt

**RED Phase starten:** Tests in `tests/unit/graph/test_manager.py` für Hierarchie-Building schreiben.
