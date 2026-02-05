# Phase 17: Code-Content Integration in GraphEnricher

> **Ziel:** Der GraphEnricher sendet echten Quellcode an das LLM, nicht nur Metadaten (Dateiname, Funktionsname, Zeilennummern). Damit werden semantische Summaries tatsächlich aussagekräftig.

---

## Problem

Aktuell sendet der GraphEnricher nur Metadaten an das LLM:

```text
1. node_id: src/auth/login.py::authenticate_user, type: function, name: authenticate_user, lines: 15-25
```

Das LLM kann nur raten, was `authenticate_user` macht. Es sieht den Code nicht.

## Lösung

Der Enricher extrahiert den echten Code zwischen `start_line` und `end_line` und sendet ihn mit:

```text
1. node_id: src/auth/login.py::authenticate_user
   type: function, lines: 15-25
   code:
   def authenticate_user(email: str, password: str) -> Token:
       user = db.get_user_by_email(email)
       if not user or not verify_password(password, user.hashed_password):
           raise InvalidCredentials()
       return create_jwt_token(user.id)
```

---

## Observations

Nach Analyse des bestehenden Codes:

- **ContentReader existiert:** `src/codemap/mapper/reader.py` - liest Dateien mit Encoding-Fallback
- **GraphEnricher hat keinen Zugriff:** Aktuell nur `GraphManager` und `LLMProvider` als Dependencies
- **MapBuilder kennt Root-Path:** Beim Build wird `root: Path` übergeben, aber nicht persistiert
- **Graph speichert relative Pfade:** Node-IDs sind relative Pfade (z.B. `src/auth/login.py`)
- **Code-Nodes haben Zeileninfo:** `start_line` und `end_line` als Attribute

## Approach

1. GraphEnricher erhält zusätzlich `root_path: Path` und `ContentReader` als Dependencies
2. Neue Methode `_extract_code_snippet()` extrahiert Code zwischen Zeilen
3. Prompt-Template erweitert um Code-Snippet pro Node
4. Token-Limit-Handling: Lange Snippets werden gekürzt mit `... (truncated)`

---

## Implementation Steps

### Phase 1: RED - Failing Tests schreiben

#### 1.1 Test-Datei erweitern

Datei: `tests/unit/engine/test_enricher.py`

Neue Test-Klasse am Ende hinzufügen:

```python
class TestEnricherCodeContent:
    """Tests for code content extraction and inclusion in prompts."""
```

#### 1.2 Test: `test_enricher_extracts_code_snippet`

**Purpose:** Verifizieren, dass Code zwischen start_line und end_line extrahiert wird.

**Setup:**

- Temporäre Python-Datei mit bekanntem Inhalt erstellen
- GraphManager mit einem Function-Node (start_line=2, end_line=4)
- GraphEnricher mit root_path und ContentReader

**Test-Datei-Inhalt:**

```python
# Line 1: Comment
def hello():  # Line 2
    return "world"  # Line 3
# Line 4: End comment

def other():  # Line 5
    pass
```

**Assertions:**

- Extrahierter Code enthält nur Zeilen 2-4
- Code beginnt mit `def hello():`
- Code endet vor `def other():`

#### 1.3 Test: `test_enricher_sends_code_in_prompt`

**Purpose:** Verifizieren, dass der Prompt den echten Code enthält.

**Setup:**

- Temporäre Python-Datei mit Funktion
- Mock LLMProvider, der den empfangenen Prompt captured
- GraphEnricher.enrich_nodes() aufrufen

**Assertions:**

- Captured Prompt enthält `code:` Label
- Captured Prompt enthält den Funktions-Body
- Captured Prompt enthält NICHT nur den Funktionsnamen

#### 1.4 Test: `test_enricher_truncates_long_code`

**Purpose:** Lange Code-Snippets werden gekürzt, um Token-Limit nicht zu sprengen.

**Setup:**

- Datei mit sehr langer Funktion (500+ Zeilen)
- GraphEnricher mit max_code_lines=50 (konfigurierbar)

**Assertions:**

- Extrahierter Code hat max 50 Zeilen
- Code endet mit `... (truncated, 450 more lines)`

#### 1.5 Test: `test_enricher_handles_missing_file`

**Purpose:** Fehlende Dateien graceful handlen (z.B. Datei gelöscht nach Graph-Build).

**Setup:**

- Graph mit Node für nicht-existierende Datei
- GraphEnricher.enrich_nodes() aufrufen

**Assertions:**

- Kein Exception
- Warning geloggt
- Node wird ohne Code enriched (Fallback auf nur Metadaten)

#### 1.6 Test: `test_enricher_handles_file_read_error`

**Purpose:** Encoding-Errors graceful handlen.

**Setup:**

- Binary-Datei als "Python"-Datei im Graph
- GraphEnricher.enrich_nodes() aufrufen

**Assertions:**

- Kein Exception
- Warning geloggt
- Node wird ohne Code enriched

#### 1.7 Test: `test_enricher_without_root_path_uses_metadata_only`

**Purpose:** Backwards-Compatibility - wenn kein root_path gegeben, alter Modus.

**Setup:**

- GraphEnricher ohne root_path initialisiert
- enrich_nodes() aufrufen

**Assertions:**

- Funktioniert wie bisher (nur Metadaten)
- Kein Fehler

---

### Phase 2: GREEN - Implementation

#### 2.1 GraphEnricher Constructor erweitern

Datei: `src/codemap/engine/enricher.py`

**Änderung an `__init__`:**

```python
def __init__(
    self,
    graph_manager: GraphManager,
    llm_provider: LLMProvider,
    root_path: Path | None = None,
    content_reader: ContentReader | None = None,
    max_code_lines: int = 100,
) -> None:
    """Initialize GraphEnricher with dependencies.

    Args:
        graph_manager: GraphManager instance containing the code graph to enrich.
        llm_provider: LLMProvider instance for AI-powered semantic analysis.
        root_path: Optional root path of the project. If provided, enables
            code content extraction for more accurate semantic analysis.
            If None, enricher falls back to metadata-only mode.
        content_reader: Optional ContentReader for reading file contents.
            If None and root_path is provided, a default ContentReader is created.
        max_code_lines: Maximum lines of code to include per snippet (default: 100).
            Longer snippets are truncated with indicator.

    Example:
        >>> # Full mode with code content
        >>> enricher = GraphEnricher(
        ...     graph_manager, llm_provider,
        ...     root_path=Path("src"),
        ...     max_code_lines=50
        ... )
        >>>
        >>> # Metadata-only mode (backwards compatible)
        >>> enricher = GraphEnricher(graph_manager, llm_provider)
    """
    self._graph_manager = graph_manager
    self._llm_provider = llm_provider
    self._root_path = root_path
    self._max_code_lines = max_code_lines

    # Create default ContentReader if root_path provided but no reader
    if root_path is not None and content_reader is None:
        self._content_reader: ContentReader | None = ContentReader()
    else:
        self._content_reader = content_reader
```

#### 2.2 Neue Methode: `_extract_code_snippet`

```python
def _extract_code_snippet(
    self,
    node_id: str,
    start_line: int,
    end_line: int,
) -> str | None:
    """Extract code snippet from file for a given node.

    Reads the source file and extracts lines between start_line and end_line
    (inclusive, 1-indexed). If the snippet exceeds max_code_lines, it is
    truncated with an indicator.

    Args:
        node_id: The node ID (used to derive file path, format: "path/file.py::name").
        start_line: Starting line number (1-indexed, inclusive).
        end_line: Ending line number (1-indexed, inclusive).

    Returns:
        The extracted code snippet as a string, or None if extraction fails
        (file not found, read error, etc.). Truncated snippets end with
        "... (truncated, N more lines)".

    Note:
        Returns None if root_path is not configured (metadata-only mode).
    """
    if self._root_path is None or self._content_reader is None:
        return None

    # Extract file path from node_id (format: "path/to/file.py::function_name")
    if "::" not in node_id:
        return None

    file_path_str = node_id.split("::")[0]
    file_path = self._root_path / file_path_str

    # Read file content
    try:
        content = self._content_reader.read_file(file_path)
    except (FileNotFoundError, ContentReadError) as e:
        logger.warning(f"Could not read file for node {node_id}: {e}")
        return None

    # Split into lines and extract range (1-indexed to 0-indexed)
    lines = content.splitlines()
    start_idx = max(0, start_line - 1)
    end_idx = min(len(lines), end_line)

    snippet_lines = lines[start_idx:end_idx]
    total_lines = len(snippet_lines)

    # Truncate if too long
    if total_lines > self._max_code_lines:
        truncated_lines = snippet_lines[: self._max_code_lines]
        remaining = total_lines - self._max_code_lines
        truncated_lines.append(f"... (truncated, {remaining} more lines)")
        return "\n".join(truncated_lines)

    return "\n".join(snippet_lines)
```

#### 2.3 Methode `_enrich_batch` anpassen

**Prompt-Building ändern:**

```python
async def _enrich_batch(self, batch: list[tuple[str, dict[str, Any]]]) -> None:
    """Enrich a single batch of code nodes with LLM analysis."""
    try:
        # Step 1: Build prompt
        system_prompt = (
            "You are a code analysis assistant. Analyze the following code elements "
            "and return a JSON array with summary and risks for each. "
            "Base your analysis on the actual code provided, not just the names."
        )

        user_prompt_lines = ["Analyze these code elements:\n"]

        for idx, (node_id, attrs) in enumerate(batch, start=1):
            start_line = attrs.get("start_line", 0)
            end_line = attrs.get("end_line", 0)
            node_type = attrs.get("type", "unknown")
            name = attrs.get("name", "unknown")

            # Try to extract code snippet
            code_snippet = self._extract_code_snippet(node_id, start_line, end_line)

            user_prompt_lines.append(f"### {idx}. {node_id}")
            user_prompt_lines.append(f"- type: {node_type}")
            user_prompt_lines.append(f"- name: {name}")
            user_prompt_lines.append(f"- lines: {start_line}-{end_line}")

            if code_snippet:
                user_prompt_lines.append("- code:")
                user_prompt_lines.append("```python")
                user_prompt_lines.append(code_snippet)
                user_prompt_lines.append("```")
            else:
                user_prompt_lines.append("- code: (not available)")

            user_prompt_lines.append("")  # Blank line between entries

        user_prompt_lines.append(
            'Return JSON array: [{"node_id": "...", "summary": "...", "risks": ["..."]}]'
        )
        user_prompt = "\n".join(user_prompt_lines)

        # Rest of method unchanged...
```

#### 2.4 Import hinzufügen

Am Anfang von `enricher.py`:

```python
from codemap.mapper.reader import ContentReader, ContentReadError
```

---

### Phase 3: REFACTOR - 100% Coverage sicherstellen

#### 3.1 Tests ausführen

```bash
pytest tests/unit/engine/test_enricher.py -v --cov=src/codemap/engine/enricher --cov-report=term-missing
```

#### 3.2 Fehlende Branches testen

Mögliche fehlende Coverage:

- `node_id` ohne `::` (kein File-Path ableitbar)
- `start_line > end_line` (ungültige Range)
- Leere Datei
- Datei mit weniger Zeilen als `end_line`

#### 3.3 Docstrings vervollständigen

- Module-Docstring erweitern um Code-Content Feature
- Alle neuen Parameter dokumentieren
- Beispiele für beide Modi (mit/ohne root_path)

#### 3.4 Type-Checking

```bash
mypy src/codemap/engine/enricher.py --strict
```

#### 3.5 Linting

```bash
ruff check src/codemap/engine/enricher.py
ruff format src/codemap/engine/enricher.py
```

---

## Beispiel: Vorher vs. Nachher

### Vorher (nur Metadaten)

```text
Analyze these code elements:
1. node_id: src/auth/login.py::authenticate_user, type: function, name: authenticate_user, lines: 15-25
```

**LLM Antwort (geraten):**

```json
[{"node_id": "src/auth/login.py::authenticate_user", "summary": "Authenticates a user", "risks": []}]
```

### Nachher (mit Code)

```text
Analyze these code elements:

### 1. src/auth/login.py::authenticate_user
- type: function
- name: authenticate_user
- lines: 15-25
- code:
` ``python
def authenticate_user(email: str, password: str) -> Token:
    user = db.get_user_by_email(email)
    if not user or not verify_password(password, user.hashed_password):
        raise InvalidCredentials()
    return create_jwt_token(user.id)
` ``
```

**LLM Antwort (informiert):**

```json
[{
  "node_id": "src/auth/login.py::authenticate_user",
  "summary": "Authenticates user by email/password, returns JWT token on success",
  "risks": [
    "SQL injection if db.get_user_by_email not parameterized",
    "Timing attack possible in password comparison",
    "No rate limiting visible"
  ]
}]
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `tests/unit/engine/test_enricher.py` | MODIFY | Neue TestEnricherCodeContent Klasse |
| `src/codemap/engine/enricher.py` | MODIFY | Constructor + _extract_code_snippet + Prompt |

---

## Dependencies

Keine neuen Dependencies erforderlich. ContentReader existiert bereits.

---

## Success Criteria

- [ ] Tests für Code-Extraktion geschrieben und grün
- [ ] `_extract_code_snippet()` implementiert
- [ ] Prompt enthält echten Code
- [ ] Truncation bei langen Snippets funktioniert
- [ ] Graceful Handling bei fehlenden/unlesbaren Dateien
- [ ] Backwards-Compatibility: Ohne root_path funktioniert alter Modus
- [ ] 100% Code Coverage
- [ ] mypy strict passing
- [ ] ruff check passing

---

## Risiken & Mitigations

| Risiko | Mitigation |
|--------|------------|
| Token-Limit bei großen Funktionen | `max_code_lines` Parameter, Default 100 |
| Encoding-Probleme | ContentReader hat bereits Fallback-Logik |
| Datei seit Graph-Build geändert | Warning loggen, mit Metadaten fortfahren |
| Performance bei vielen Dateien | ContentReader cached nicht, aber Batching hilft |

---

## Nächste Phase

Nach Abschluss von Phase 17 ist die Grundlage für aussagekräftige Summaries gelegt.
Phase 18 (Hierarchische Aggregation) kann dann auf echten Code-Summaries aufbauen.
