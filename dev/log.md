# Development Log - codemap

## Phase 1: Basis-Projektstruktur und Dependencies

### #001 - 2025-12-11 18:25
**Aktion:** Ordnerstruktur erstellt
**Warum:** Grundlegendes src/-Layout für Python-Projekt mit TDD-Enforcement benötigt
**Ergebnis:**
- `src/codemap/` und `src/codemap/core/` mit `__init__.py`
- `tests/` und `tests/unit/` mit `__init__.py`
- `tests/conftest.py` (leer, für pytest-Fixtures)
- `docs/` Verzeichnis

### #002 - 2025-12-11 18:25
**Aktion:** .gitignore erstellt
**Warum:** Python-Artefakte, IDE-Dateien, Cache-Verzeichnisse vom Versionskontrolle ausschließen
**Ergebnis:** Umfassende .gitignore mit Einträgen für Python, venv, pytest, mypy, ruff, MkDocs

### #003 - 2025-12-11 18:25
**Aktion:** requirements-dev.txt erstellt
**Warum:** Alle Development-Dependencies zentral definieren
**Ergebnis:** 11 Dependencies (pydantic, tree-sitter, pytest, ruff, mypy, mkdocs-material, etc.)

### #004 - 2025-12-11 18:25
**Aktion:** pyproject.toml erstellt
**Warum:** Moderne Python-Projektkonfiguration mit setuptools und Metadaten
**Ergebnis:** Build-System, Projekt-Metadaten, src/-Layout konfiguriert

### #005 - 2025-12-11 18:41
**Aktion:** README.md erstellt
**Warum:** pyproject.toml referenziert readme = "README.md", Datei fehlte
**Ergebnis:** Platzhalter-README mit Projektname und Kurzbeschreibung

### #006 - 2025-12-11 19:15
**Aktion:** Strikte TDD-Tooling-Konfiguration in pyproject.toml
**Warum:** TDD-Enforcement mit 100% Coverage-Anforderung, Type-Checking und Linting benötigt
**Ergebnis:**
- `[tool.pytest.ini_options]` - Auto-Coverage, strict markers, Test-Patterns
- `[tool.coverage.report]` - fail_under=100, 8 exclude_lines Patterns
- `[tool.coverage.run]` - Source-Beschränkung, Branch-Coverage
- `[tool.mypy]` - strict=true mit 9 zusätzlichen Type-Checking Flags
- `[tool.ruff]` - line-length=100, E/F/I/N/W Rules, Auto-Fix
- `[tool.ruff.lint]` + `[tool.ruff.format]` Sub-Sektionen
- Bugfix: `if __name__ == "__main__":` Pattern mit korrektem TOML-Escaping

## Phase 1: MkDocs Dokumentation mit Material Theme

### #007 - 2025-12-11 19:45
**Aktion:** MkDocs-Konfiguration erstellt (mkdocs.yml)
**Warum:** Automatische API-Dokumentation mit Material Theme für professionelle Dark-Mode-Ästhetik
**Ergebnis:**
- Material Theme mit scheme: slate, primary: teal
- Features: navigation.instant, navigation.sections, content.code.copy
- mkdocstrings Plugin mit handlers.python.paths: [src], Google-style docstrings
- Navigation: Home (index.md), API Reference (api.md)

### #008 - 2025-12-11 19:50
**Aktion:** Dokumentations-Startseite erstellt (docs/index.md)
**Warum:** Welcome-Page mit TDD-Philosophie und Getting Started Guide benötigt
**Ergebnis:**
- Welcome Section mit Projektbeschreibung
- Key Features: TDD, Type Safety, Modern Tooling, Auto API Docs
- Getting Started: Installation und pytest Commands
- Philosophy: Red → Green → Refactor Workflow erklärt
- Bugfix: Link zu api.md korrigiert (war api/index.md)

### #009 - 2025-12-11 19:55
**Aktion:** API-Referenz-Seite erstellt (docs/api.md)
**Warum:** mkdocstrings-Direktive für automatische Docstring-Generierung
**Ergebnis:**
- ::: codemap.core Direktive mit Options (show_root_heading, show_source, members_order)
- Placeholder-Kommentare für zukünftige Module (parsers, utils)

### #010 - 2025-12-11 20:05
**Aktion:** Build-Probleme behoben
**Warum:** codemap.core war leer, CONTRIBUTING.md fehlte → mkdocs build würde scheitern
**Ergebnis:**
- src/codemap/core/__init__.py: Minimale Python-Struktur mit Docstring und __all__
- CONTRIBUTING.md: Platzhalter mit TDD-Workflow-Beschreibung
- Verifiziert: `mkdocs build` erfolgreich (0.80 Sekunden)

## Phase 1: TDD Proof-of-Concept - Smoke Tests und initiale Code-Basis

### #011 - 2025-12-11 20:30
**Aktion:** TDD Proof-of-Concept implementiert
**Warum:** Validierung der strikten TDD-Toolchain (pytest, 100% Coverage, mypy strict, ruff)
**Ergebnis:**
- `src/codemap/__init__.py`: `__version__ = "0.1.0"` hinzugefügt
- `tests/unit/test_smoke.py`: Smoke Test `test_basic_math()` (pytest-Discovery verifiziert)
- `tests/unit/test_version.py`: `test_version_exists()` und `test_core_module_exists()`
- Alle Quality Gates bestanden: 3 Tests passed, 100% Coverage, mypy clean, ruff clean
- Code-Review: APPROVED - TDD-Prinzipien korrekt angewendet

### #012 - 2025-12-11 20:35
**Aktion:** Review-Feedback implementiert
**Warum:** `test_core_module_exists()` definierte unnötigen API-Kontrakt für `core.__all__`
**Ergebnis:**
- Test gelockert: Prüft nur Importierbarkeit von `core`, nicht mehr `__all__`-Struktur
- Hinweis dokumentiert: Version `"0.1.0"` an 3 Stellen hartkodiert (pyproject.toml, __init__.py, test) - mittelfristig zentralisieren

## Phase 1: Workflow-Dokumentation und Verifikation

### #013 - 2025-12-11 19:43
**Aktion:** CONTRIBUTING.md erweitert - TDD Workflow Dokumentation
**Warum:** Developer-facing Dokumentation für TDD-Workflow (Red-Green-Refactor) mit allen Commands benötigt
**Ergebnis:**
- Header mit TDD-Statement, Red-Green-Refactor Cycle (4 Schritte)
- Development Commands Section (pip, pytest, mypy, ruff, mkdocs)
- Coverage Requirements mit allen 6 Excluded Patterns aus pyproject.toml
- Pull Request Checklist mit Conventional Commits Link
- Code-Review: Minor Issues behoben (fehlende Exclusions, pytest flags)

### #014 - 2025-12-11 19:44
**Aktion:** README.md erweitert - Projekt Landing Page
**Warum:** Professionelle Einstiegsseite mit Installation, Quick Start und Projektstruktur
**Ergebnis:**
- Header mit Badges (Python, License, Coverage)
- Overview mit 5 Key Features (TDD, Type Safety, Auto Docs, Code Quality, Modern Layout)
- Installation (4-Schritt-Anleitung) und Quick Start Section
- Project Structure Tree, Documentation Links, License

### #015 - 2025-12-11 19:48
**Aktion:** setup_check.py erstellt (TDD)
**Warum:** Automatisches Verifikationsskript für gesamte Toolchain mit einem Command
**Ergebnis:**
- `run_command()` Funktion mit subprocess und Emoji-Feedback (✓/✗)
- `main()` mit 7 Verifikationsschritten (Python-Version, pip, pytest, mypy, ruff, mkdocs)
- 15 Unit-Tests in tests/unit/test_setup_check.py (100% Coverage)
- Strikt nach TDD: Tests zuerst geschrieben (Red), dann Implementation (Green)

### #016 - 2025-12-11 19:52
**Aktion:** setup_check.sh erstellt
**Warum:** Shell-Alternative für Unix-Systeme
**Ergebnis:** Bash-Script mit set -euo pipefail, alle 7 Verifikationsschritte

### #017 - 2025-12-11 19:53
**Aktion:** docs/index.md aktualisiert - Contributing Section
**Warum:** Link zum Contributing Guide in Dokumentation benötigt
**Ergebnis:**
- Contributing Section nach Philosophy hinzugefügt
- Link zu CONTRIBUTING.md (ohne Markdown-Link wegen MkDocs strict mode)

### #018 - 2025-12-11 20:05
**Aktion:** Review-Feedback implementiert - Installationsanleitung
**Warum:** docs/index.md nutzte `pip install -e ".[dev]"`, aber [dev] in pyproject.toml leer
**Ergebnis:** Installationsanleitung auf `pip install -r requirements-dev.txt` geändert (konsistent mit README)

### #019 - 2025-12-11 20:08
**Aktion:** Review-Feedback implementiert - Projektnamen vereinheitlicht
**Warum:** Inkonsistenz zwischen "Codemap" und "ContextCurator" in Dokumentation
**Ergebnis:**
- README.md: Projektstruktur-Baum und cd-Befehl auf "codemap" geändert
- Alle Dateien konsistent: Codemap (Titel), codemap (Package-Name)

### #020 - 2025-12-11 20:12
**Aktion:** Review-Feedback implementiert - pip-Aufruf verbessert
**Warum:** `["pip", ...]` kann Umgebungsprobleme verursachen
**Ergebnis:** setup_check.py nutzt jetzt `[sys.executable, "-m", "pip", ...]` für korrektes venv

### #021 - 2025-12-11 20:15
**Aktion:** Review-Feedback implementiert - Python-Versionsprüfung zukunftssicher
**Warum:** `major >= 3 and minor >= 11` funktioniert nicht für Python 4.x
**Ergebnis:**
- setup_check.py: `sys.version_info[:2] >= (3, 11)` (Tuple-Vergleich)
- Tests: `__getitem__` zu allen version_info Mocks hinzugefügt

### #022 - 2025-12-11 20:18
**Aktion:** Review-Feedback implementiert - setup_check.sh als Wrapper
**Warum:** Duplizierte Logik in setup_check.sh kann divergieren
**Ergebnis:**
- setup_check.sh auf 10 Zeilen reduziert: `exec python setup_check.py "$@"`
- Python bleibt Single Source of Truth mit vollständigen Tests

## Phase 2: TreeGenerator - TDD Red Phase

### #023 - 2025-12-11 21:30
**Aktion:** Test-Suite für TreeGenerator erstellt (Red Phase)
**Warum:** TDD erfordert Tests vor Implementation; TreeGenerator visualisiert Verzeichnisstrukturen
**Ergebnis:**
- `tests/unit/scout/__init__.py` erstellt (Package-Struktur)
- `tests/unit/scout/test_tree.py` mit 22 Tests in 6 Klassen:
  - TestTreeGeneratorBasic (4 Tests): Rückgabetyp, leere Ordner, einzelne Datei/Ordner
  - TestTreeGeneratorMaxDepth (4 Tests): max_depth 0, 1, 2 (default), 3
  - TestTreeGeneratorIgnoreHidden (4 Tests): .git, .venv, __pycache__ Filterung
  - TestTreeGeneratorSorting (3 Tests): Alphabetische Sortierung
  - TestTreeGeneratorFormat (3 Tests): Tree-Symbole (├──, └──), Einrückung
  - TestTreeGeneratorEdgeCases (4 Tests): ValueError für ungültige Pfade, negatives max_depth
- Red Phase verifiziert: `ModuleNotFoundError: No module named 'codemap.scout'`

### #024 - 2025-12-11 21:45
**Aktion:** Review-Feedback - Exception-Typen präzisiert
**Warum:** Tests erlaubten mehrere Exception-Typen, API-Vertrag definiert nur ValueError
**Ergebnis:**
- `test_generate_with_nonexistent_path`: `pytest.raises(ValueError, match="Path does not exist")`
- `test_generate_with_file_instead_of_directory`: `pytest.raises(ValueError, match="Path is not a directory")`
- `test_generate_raises_error_for_negative_max_depth`: Neuer Test hinzugefügt

### #025 - 2025-12-11 21:50
**Aktion:** Review-Feedback - Format-Test für exakten Vergleich
**Warum:** Schleife mit `in`-Operator tolerierte fehlende/zusätzliche Zeilen
**Ergebnis:**
- `test_generate_tree_structure_format`: `result.strip().splitlines() == expected.splitlines()`
- Prüft jetzt Reihenfolge und Vollständigkeit, nicht nur Vorhandensein

### #026 - 2025-12-11 21:55
**Aktion:** Review-Feedback - Indentation-Test robuster gemacht
**Warum:** Nur Leerzeichen-Zählung ignorierte Tree-Symbole und vertikale Linien
**Ergebnis:**
- `test_generate_indentation_consistency`: Pattern-basierte Validierung
- Akzeptiert `    ├──` und `│   ├──` als gültige Level-2-Prefixes
- Level-Relation-Check: Tiefere Level müssen mehr Einrückung haben

## Phase 2: TreeGenerator - TDD Green Phase

### #027 - 2025-12-11 23:15
**Aktion:** TreeGenerator implementiert (Green Phase)
**Warum:** Red-Phase-Tests definieren das erwartete Verhalten; Implementation muss alle 22 Tests bestehen
**Ergebnis:**
- `src/codemap/scout/__init__.py`: Package mit `TreeGenerator` Export
- `src/codemap/scout/tree.py`: Vollständige Implementation
  - `IGNORED_DIRS`: `.git`, `.venv`, `__pycache__`
  - Tree-Symbole: `├──`, `└──`, `│`, 4-Space-Einrückung
  - `generate(root_path, max_depth=2)`: Public API mit Validierung
  - `_should_ignore(path)`: Filtert ignorierte Verzeichnisse
  - `_generate_tree()`: Rekursive Generierung mit depth-abhängiger Tiefenzählung
- **Besonderheit max_depth:** Dateien haben effektive Tiefe = depth-1 bei depth>=3 (sonst depth)
- 22/22 Tests bestanden, 100% Coverage für `tree.py`

### #028 - 2025-12-11 23:20
**Aktion:** Test-Korrektur - Widerspruch in Tests behoben
**Warum:** `test_generate_tree_structure_format` erwartete `helper.py` nicht bei max_depth=2, aber `test_generate_respects_max_depth_default` verlangte es explizit
**Ergebnis:**
- Format-Test korrigiert: `helper.py` in expected_lines aufgenommen
- Begründung: max_depth-Tests sind autoritativ für Tiefenverhalten

### #029 - 2025-12-11 23:25
**Aktion:** Code-Qualität verifiziert
**Warum:** TDD erfordert strikte Qualitätsprüfung nach Green Phase
**Ergebnis:**
- mypy: Success, no issues found
- ruff check: All checks passed
- ruff format: Applied (Listenkomposition einzeilig formatiert)
- Coverage: 100% für `src/codemap/scout/tree.py`

## Phase 3: TreeGenerator Refactoring - TreeReport Datenmodell

### #030 - 2025-12-11 23:45
**Aktion:** TreeReport Dataclass und Test-Suite Refactoring (TDD Red Phase)
**Warum:** Plan 01 erfordert strukturierte Rückgabe statt String, unlimited depth, .gitignore-Support
**Ergebnis:**
- `src/codemap/scout/models.py` NEU: TreeReport Dataclass mit 4 Feldern
  - `tree_string: str`, `total_files: int`, `total_folders: int`, `estimated_tokens: int`
- `tests/unit/scout/test_tree.py` REFACTORED:
  - Import `TreeReport` hinzugefügt
  - `TestTreeGeneratorMaxDepth` Klasse komplett entfernt (4 Tests)
  - `test_generate_raises_error_for_negative_max_depth` entfernt
  - Alle Tests auf `result.tree_string` umgestellt
  - 4 neue Tests: `test_returns_report_object`, `test_deep_nesting`, `test_respects_gitignore`, `test_gitignore_directory_pattern`
- Red Phase verifiziert: 19 failed, 2 passed (AttributeError: 'str' has no attribute 'tree_string')

### #031 - 2025-12-11 23:55
**Aktion:** TreeGenerator auf TreeReport umgestellt (TDD Green Phase)
**Warum:** Tests erwarten TreeReport-Objekte statt Strings
**Ergebnis:**
- `src/codemap/scout/tree.py` REFACTORED:
  - `generate()` gibt `TreeReport` zurück statt `str`
  - `max_depth` Parameter komplett entfernt
  - `_generate_tree()` ohne depth-Parameter (unlimited depth)
  - Counter `_file_count`, `_folder_count` für Statistiken
  - `estimated_tokens = int(len(tree_string) / 3.5)`
- 19/21 Tests bestanden (2 .gitignore-Tests noch fehlend)

### #032 - 2025-12-12 00:05
**Aktion:** .gitignore-Integration mit pathspec implementiert
**Warum:** Tests `test_respects_gitignore` und `test_gitignore_directory_pattern` erforderten Pattern-Matching
**Ergebnis:**
- `import pathspec` hinzugefügt
- `IGNORED_FILES = {".gitignore"}` für Meta-Dateien
- `_load_gitignore()`: Liest und kompiliert .gitignore mit `pathspec.PathSpec.from_lines("gitwildmatch", ...)`
- `_should_ignore()` erweitert: Prüft IGNORED_DIRS, IGNORED_FILES, dann PathSpec
- Directories erhalten trailing `/` für korrekte Pattern-Matching
- 21/21 Tests bestanden, 100% Coverage für `tree.py`

### #033 - 2025-12-12 00:15
**Aktion:** Test für estimated_tokens Formel hinzugefügt
**Warum:** Verifikationskommentar forderte Test, der Formel `int(len(tree_string) / 3.5)` explizit prüft
**Ergebnis:**
- `test_estimated_tokens_matches_formula` NEU:
  - Erstellt deterministische Baumstruktur (2 Dateien)
  - Verifiziert: `result.estimated_tokens == int(len(result.tree_string) / 3.5)`
  - Sanity-Checks: tokens > 0, tokens < string length
- 22/22 Tests bestanden, 100% Coverage für `tree.py`

### #034 - 2025-12-12 00:30
**Aktion:** TreeReport Export in scout/__init__.py hinzugefügt
**Warum:** Plan Step 3 forderte Export von TreeReport aus dem scout Package
**Ergebnis:**
- `from codemap.scout.models import TreeReport` hinzugefügt
- `__all__ = ["TreeGenerator", "TreeReport"]`
- Module Docstring erweitert
- 41/41 Tests bestanden, 100% Coverage

### #035 - 2025-12-12 00:45
**Aktion:** TreeGenerator Instanzzustand entfernt (Stateless Refactoring)
**Warum:** Verifikationskommentar: `_file_count`, `_folder_count`, `_root_path`, `_gitignore_spec` als Instanzfelder erschweren parallele/reentrant Nutzung
**Ergebnis:**
- `__init__()` enthält keine Felder mehr
- `generate()` nutzt lokale `stats: dict[str, int]` und `gitignore_spec`
- `_generate_tree(path, prefix, root_path, gitignore_spec, stats)` erhält alle Parameter
- `_should_ignore(path, root_path, gitignore_spec)` erhält alle Parameter
- Thread-safe und reentrant nutzbar
- 41/41 Tests bestanden, 100% Coverage

### #036 - 2025-12-12 01:00
**Aktion:** Windows-Pfadnormalisierung für .gitignore-Matching
**Warum:** Verifikationskommentar: Backslashes (Windows) könnten falsche Matches ergeben
**Ergebnis:**
- `_should_ignore()`: `pattern_path = str(relative_path).replace("\\", "/")`
- Trailing Slash für Directories nach Normalisierung hinzugefügt
- Cross-Platform-Kompatibilität für Windows-Pfade sichergestellt
- 41/41 Tests bestanden, 100% Coverage

### #037 - 2025-12-12 01:15
**Aktion:** Fehlerbehandlung für .gitignore-Lesen hinzugefügt
**Warum:** Verifikationskommentar: PermissionError oder Encoding-Probleme könnten Traversierung abbrechen
**Ergebnis:**
- `_load_gitignore()`: try/except für `OSError` und `UnicodeError`
- Bei Fehler wird `None` zurückgegeben (keine .gitignore-Filterung)
- TODO-Kommentar für zukünftiges Logging hinzugefügt
- `test_gitignore_unreadable_continues_traversal` NEU: Verifiziert graceful degradation
- 42/42 Tests bestanden, 100% Coverage

### #038 - 2025-12-12 01:30
**Aktion:** Fehlerbehandlung für iterdir() bei Permission-Fehlern
**Warum:** Verifikationskommentar: PermissionError bei iterdir() könnte Traversierung abbrechen
**Ergebnis:**
- `_generate_tree()`: try/except für `OSError` um `path.iterdir()`
- Bei Fehler wird leere Liste zurückgegeben (Verzeichnis wird still übersprungen)
- Kommentar: "Silently skip directories that cannot be read"
- `test_generate_skips_unreadable_directory` NEU: Verifiziert graceful degradation
- 43/43 Tests bestanden, 100% Coverage

## Phase 4: LLM Provider Interface - Test-Verbesserungen

### #039 - 2025-12-12 14:30
**Aktion:** Code-Review-Feedback für LLM Provider Tests implementiert
**Warum:** Code-Review identifizierte 6 Issues: mypy-Fehler, irreführende Tests, zu strikte Assertions, fehlende Protocol-Konformitätstests, inkonsistente Parameternamen
**Ergebnis:**
- `test_llm_provider_is_protocol`: Fix für mypy type error (`issubclass(X, Protocol)` → `getattr(X, "_is_protocol")`)
- `test_cerebras_provider_init_has_docstring`: Entfernt (irreführend, nutzte Python's Default-Docstring)
- `test_get_provider_unknown_raises_value_error`, `test_get_provider_invalid_provider_raises_value_error`: Weniger strikte Assertions (Substring-Check statt exakter String-Vergleich)
- `test_llm_provider_has_docstring`, `test_send_method_has_docstring`: Flexiblere Assertions (generische Keywords statt exakte Formulierungen)
- `test_factory_returns_protocol_conformant_provider` NEU: Demonstriert Protocol-Konformität mit Hilfsfunktion `use_provider(provider: LLMProvider)`
- `MockProvider.send`: Parameternamen von `_system`/`_user` zu `system`/`user` geändert (konsistent mit Protocol)
- 49 Tests bestanden, 100% Coverage für codemap.core, mypy clean

## Phase 4: StructureAdvisor - LLM-basierte Verzeichnisanalyse

### #040 - 2025-12-12 16:30
**Aktion:** StructureAdvisor mit Dependency Injection implementiert (TDD)
**Warum:** Plan 03 erfordert LLM-basierte Analyse von TreeReport zur Identifikation von Non-Source-Dateien
**Ergebnis:**
- `src/codemap/scout/advisor.py` NEU:
  - `SYSTEM_PROMPT`: Modul-Level-Konstante für LLM-Anweisungen (German)
  - `StructureAdvisor.__init__(provider: LLMProvider)`: Constructor-based DI
  - `StructureAdvisor.analyze(report: TreeReport) -> list[str]`: Analysemethode
  - Prompt-Format: System-Prompt + `f"Hier ist der Dateibaum:\n\n{report.tree_string}"`
  - Response-Parsing: Markdown-Code-Blocks entfernen, Zeilen splitten, leere filtern
- `tests/unit/scout/test_advisor.py` NEU: 27 Tests in 6 Klassen
  - TestStructureAdvisorInitialization (5): Klassenerstellung, Provider-Storage, Protocol-Conformance
  - TestStructureAdvisorAnalyzeMethod (9): Clean Response, Markdown-Parsing, Empty/Whitespace
  - TestStructureAdvisorPromptConstruction (3): System/User-Prompt-Verifikation
  - TestStructureAdvisorSystemPromptConstant (4): Konstanten-Validierung
  - TestStructureAdvisorDocumentation (4): Docstring-Prüfung
  - TestStructureAdvisorTypeHints (2): Annotation-Verifikation
- `src/codemap/scout/__init__.py`: `StructureAdvisor` zu `__all__` hinzugefügt
- Code-Review: APPROVED (95/100), Minor Issues behoben:
  - Test-Naming: `test_analyze_strips_prefix_text` → `test_analyze_preserves_prefix_text`
  - Kosmetische Leerzeilen entfernt
- 27/27 Tests bestanden, 100% Coverage für advisor.py, mypy clean, ruff clean

### #041 - 2025-12-12 19:15
**Aktion:** API-Kontrakt für analyze() präzisiert und Parsing erweitert
**Warum:** Verifikationskommentar: SYSTEM_PROMPT fordert "NUR Pfade", aber analyze() behielt Präfix-Text bei
**Ergebnis:**
- `advisor.py`:
  - Docstring präzisiert: "return list of valid gitignore patterns only"
  - `_is_valid_pattern(line)` NEU: Heuristik für gültige Patterns (slash, asterisk, dot-prefix, no-space)
  - Erklärende Zeilen wie "Hier ist die Liste:" werden jetzt gefiltert
- `test_advisor.py`:
  - `test_analyze_preserves_prefix_text` → `test_analyze_filters_prefix_text` (Assertion invertiert)
  - `test_analyze_complex_response_with_markdown_and_prefix`: Erwartet nur Patterns, nicht Präfix
  - `test_analyze_accepts_simple_filenames_without_pattern_chars` NEU: Testet `Makefile`, `LICENSE`
- 28/28 Tests bestanden, 100% Coverage für advisor.py

### #042 - 2025-12-12 19:45
**Aktion:** Robustes Parsing für Bullet-Listen und nummerierte Listen
**Warum:** Verifikationskommentar: LLMs geben oft "- node_modules/" oder "1. dist/" zurück
**Ergebnis:**
- `advisor.py`:
  - `import re` hinzugefügt
  - Kommentarzeilen (beginnend mit `#`) werden gefiltert
  - `_normalize_line(line)` NEU:
    - `^[-*](?:\s+|$)` entfernt Bullet-Punkte (- oder *)
    - `^\d+\.(?:\s+|$)` entfernt nummerierte Präfixe (1., 2., etc.)
  - Docstring: Schritt 4 "Normalizing lines" hinzugefügt
- `test_advisor.py`:
  - `test_analyze_normalizes_bullet_list_with_dash` NEU
  - `test_analyze_normalizes_bullet_list_with_asterisk` NEU
  - `test_analyze_normalizes_numbered_list` NEU
  - `test_analyze_filters_comment_lines` NEU
  - `test_analyze_mixed_formatting` NEU
  - `test_analyze_filters_empty_bullet_points` NEU
- 34/34 Tests bestanden, 100% Coverage für advisor.py

### #043 - 2025-12-12 20:00
**Aktion:** Dedizierter TestMockProvider im Testfile erstellt
**Warum:** Verifikationskommentar: Plan forderte Test-eigenen MockProvider statt Abhängigkeit von codemap.core.llm
**Ergebnis:**
- `test_advisor.py`:
  - Import `from codemap.core.llm import MockProvider` entfernt
  - `TestMockProvider` Klasse NEU (außerhalb der Testklassen):
    - `__test__ = False` (verhindert Pytest-Collection)
    - `send(system, user) -> str`: Deterministisch "node_modules/\ndist/\n.venv/"
    - Prompt-Tracking via `last_system_prompt`, `last_user_prompt`
    - Umfassende Docstring mit Beispiel
  - 4 Tests aktualisiert: `MockProvider()` → `TestMockProvider()`
    - `test_structure_advisor_init_with_provider`
    - `test_structure_advisor_stores_provider`
    - `test_analyze_method_exists`
    - `test_analyze_has_docstring`
  - Spezialisierte Provider (`CleanProvider`, `MarkdownProvider`, etc.) beibehalten
- 34/34 Tests bestanden, 100% Coverage für advisor.py, keine Pytest-Warnungen

## Phase 5: CerebrasProvider mit OpenAI Client

### #044 - 2025-12-12 21:30
**Aktion:** OpenAI Dependency zu requirements-dev.txt hinzugefügt
**Warum:** CerebrasProvider benötigt OpenAI SDK für API-Kommunikation mit OpenAI-kompatibler Schnittstelle
**Ergebnis:**
- `requirements-dev.txt`: `openai>=1.0.0` in Core Dependencies Sektion hinzugefügt
- Drei-Sektionen-Struktur beibehalten (Core Dependencies, TDD/QA Tools, Documentation)
- Formatierung konsistent mit existierenden Einträgen

### #045 - 2025-12-12 22:00
**Aktion:** CerebrasProvider mit OpenAI Client implementiert (TDD)
**Warum:** Plan 02 erfordert echte Cerebras-API-Integration statt Stub; ermöglicht LLM-Inferenz via llama3.1-70b
**Ergebnis:**
- `src/codemap/core/llm.py` REFACTORED:
  - `import os` und `from openai import OpenAI` hinzugefügt
  - `CerebrasProvider.__init__()`: Liest `CEREBRAS_API_KEY` aus Umgebung, ValueError wenn leer
  - `CerebrasProvider.send()`: OpenAI-kompatible API-Calls mit temperature=0.2
  - Defensive Checks: ValueError bei leerer `choices`-Liste oder `None` in `message.content`
  - `# pragma: no cover` an `send()` für echte API-Calls (nicht in Tests)
- `tests/unit/core/test_llm.py` REFACTORED:
  - `import os` und `from unittest.mock import MagicMock, patch` hinzugefügt
  - 11 Tests in `TestCerebrasProvider` aktualisiert: `@patch.dict` + `@patch("codemap.core.llm.OpenAI")`
  - `test_cerebras_provider_init_requires_api_key`: Verifiziert OpenAI-Initialisierung
  - `test_cerebras_provider_init_missing_api_key`, `test_cerebras_provider_init_empty_api_key` NEU
  - `test_cerebras_provider_send_calls_openai_api` NEU: Mock-Verifizierung der API-Parameter
  - Docstring-Assertions aktualisiert: "api" statt "stub"
  - `TestGetProviderFactory`: 3 Tests mit Mocking aktualisiert
- 128 Tests bestanden, 100% Coverage, mypy clean, ruff clean

### #046 - 2025-12-12 22:15
**Aktion:** Error-Handling in StructureAdvisor.analyze() hinzugefügt
**Warum:** Verifikationskommentar: CerebrasProvider.send() kann ValueError werfen, Call-Sites müssen abfangen
**Ergebnis:**
- `src/codemap/scout/advisor.py`:
  - `import logging` und `logger = logging.getLogger(__name__)` hinzugefügt
  - `analyze()`: try/except ValueError um `_provider.send()` mit Warning-Log
  - Docstring erweitert: "Empty list if API error occurs"
- `tests/unit/scout/test_advisor.py`:
  - `test_analyze_returns_empty_list_on_provider_value_error` NEU
  - `ErrorProvider` Test-Double wirft ValueError
- 128 Tests bestanden, 100% Coverage

## Phase 5: Demo-Script für StructureAdvisor

### #047 - 2025-12-12 23:30
**Aktion:** demo_advisor.py erstellt
**Warum:** Plan 03 erfordert Demo-Script zum Demonstrieren des vollständigen Workflows (TreeGenerator → StructureAdvisor → LLM-Analyse)
**Ergebnis:**
- `demo_advisor.py` NEU im Root-Verzeichnis:
  - Imports: TreeGenerator, StructureAdvisor, get_provider (Cerebras)
  - main() mit 5 Phasen: Header, Tree-Scan, Provider-Init, LLM-Analyse, Ergebnisausgabe
  - Timing-Messungen für Scan und Analyse separat
  - Emoji-basierte Konsolen-Ausgabe (konsistent mit demo_tree.py)
  - Statistik-Zusammenfassung: Dateien, Ordner, Patterns, Dauer
- Error-Handling:
  - ImportError: sys.exit(1) mit Details
  - Scan-Fehler: sys.exit(1) mit Fehlermeldung
  - ValueError (missing API key): sys.exit(1) mit Setup-Tipp
  - Analyse-Fehler: sys.exit(1) mit Fehlermeldung
- Syntax-Verifikation: ✅ py_compile erfolgreich
- Import-Verifikation: ✅ Alle Module gefunden
- Exit-Code-Verifikation: ✅ Code 1 bei fehlendem CEREBRAS_API_KEY

### #048 - 2025-12-12 23:35
**Aktion:** Konsistentes Exit-Code-Verhalten für Demo-Scripts
**Warum:** Verifikationskommentar: Fehlerfälle sollten Exit-Code 1 signalisieren statt still mit return zu enden
**Ergebnis:**
- `demo_advisor.py`: 3x `return` → `sys.exit(1)` (Scan-Fehler, API-Key-Fehler, Analyse-Fehler)
- `demo_tree.py`: 1x `return` → `sys.exit(1)` (Scan-Fehler)
- Beide Demo-Scripts verhalten sich jetzt konsistent bei Fehlern
- Verifiziert: Exit-Code 1 bei fehlendem API-Key bestätigt

## Phase 6: FileEntry Datenmodell

### #049 - 2025-12-13 10:30
**Aktion:** FileEntry Dataclass implementiert (TDD)
**Warum:** Plan 01 erfordert immutables Datenmodell für File-Metadaten mit Pfad, Größe und Token-Schätzung
**Ergebnis:**
- `src/codemap/scout/models.py` ERWEITERT:
  - `from pathlib import Path` Import hinzugefügt
  - `FileEntry` frozen Dataclass mit 3 Attributen:
    - `path: Path` - Relativer Pfad vom Projekt-Root
    - `size: int` - Dateigröße in Bytes
    - `token_est: int` - Token-Schätzung (size / 4)
  - Docstring im TreeReport-Stil mit Beispiel
- `tests/unit/scout/test_models.py` NEU:
  - 6 Tests für FileEntry: Creation, Immutability, Attribute Access, Relative Paths, Equality
  - 2 Tests für TreeReport (Regression)
- `tests/unit/scout/test_init.py` NEU:
  - 4 Tests für Public API Export: FileEntry in __all__, alphabetische Sortierung
- `src/codemap/scout/__init__.py` ERWEITERT:
  - `FileEntry` zu Import und `__all__` hinzugefügt
  - Alphabetische Sortierung: `["FileEntry", "StructureAdvisor", "TreeGenerator", "TreeReport"]`
- 71/71 Scout-Tests bestanden, 100% Coverage für models.py

### #050 - 2025-12-13 10:45
**Aktion:** FileEntry Docstring-Korrekturen (Review-Feedback)
**Warum:** Verifikationskommentare: Docstring behauptete "absolute or relative" aber Plan fordert nur relative Pfade
**Ergebnis:**
- `path` Attribut: "Relative file path from the project root as a Path object."
- Beispiel: `Path("src/main.py")` statt `Path("/project/src/main.py")`
- `token_est` Attribut: "calculated as size / 4 rounded to int." ergänzt
- Konsistenz mit TreeReport.estimated_tokens Dokumentationsformat
- Beispiel-Werte konsistent: size=1024, token_est=256 (1024/4=256)

## Phase 6: FileWalker - TDD RED Phase

### #051 - 2025-12-13 14:30
**Aktion:** FileWalker Test-Suite erstellt (TDD RED Phase)
**Warum:** Plan 02 erfordert umfassende Tests für FileWalker vor Implementation
**Ergebnis:**
- `tests/unit/scout/test_walker.py` NEU: 26 Tests in 6 Klassen
  - TestFileWalkerBasic (4 Tests): Rückgabetyp, leere Verzeichnisse, einzelne Datei, verschachtelte Strukturen
  - TestFileWalkerPatterns (4 Tests): Einzelne/multiple Patterns, Directory-Patterns, Wildcard-Patterns
  - TestFileWalkerDefaultIgnores (4 Tests): .git, .venv, __pycache__ automatisch ignoriert
  - TestFileWalkerMetadata (5 Tests): Size-Berechnung, Token-Formel (size // 4), relative Pfade, leere Dateien
  - TestFileWalkerSorting (3 Tests): Alphabetisch, verschachtelt, deterministisch
  - TestFileWalkerEdgeCases (6 Tests): Permission-Errors, tiefe Verschachtelung, Sonderzeichen, ValueError für ungültige Pfade
- RED Phase verifiziert: `ImportError: cannot import name 'FileEntry'` (strikt TDD)

### #052 - 2025-12-13 14:45
**Aktion:** Strikt TDD RED Phase - FileEntry temporär entfernt
**Warum:** Verifikationskommentar: FileEntry existierte bereits, aber RED Phase soll beide Imports fehlschlagen lassen
**Ergebnis:**
- `src/codemap/scout/models.py`: FileEntry Klasse entfernt (wird in GREEN Phase re-implementiert)
- `src/codemap/scout/__init__.py`: FileEntry aus Import und `__all__` entfernt
- `tests/unit/scout/test_models.py`: TestFileEntry Tests schlagen nun ebenfalls fehl (konsistente RED Phase)
- `tests/unit/scout/test_tree.py`: 24 Tests bestanden (keine FileEntry-Abhängigkeit)
- RED Phase verifiziert: Beide Imports `FileEntry` und `FileWalker` erzeugen Fehler

### #053 - 2025-12-13 15:00
**Aktion:** ValueError-Test präzisiert und fehlende Tests ergänzt (Review-Feedback)
**Warum:** Verifikationskommentar: try/except im Test war mehrdeutig; Plan forderte weitere Tests für 100% Coverage
**Ergebnis:**
- `test_walker_nonexistent_path`: `pytest.raises(ValueError, match="Path does not exist")` analog zu test_tree.py
- `test_walker_nested_structure` NEU: src/main.py und tests/test_main.py mit relativen Pfaden
- `test_walker_respects_wildcard_patterns` NEU: test_*.py Pattern-Matching
- `test_walker_calculates_size_correctly` NEU: Mehrere Dateigrößen (50, 200, 1000 Bytes)
- `test_walker_handles_empty_files` NEU: 0 Bytes → size=0, token_est=0
- `test_walker_sorting_is_deterministic` NEU: Identische Reihenfolge bei wiederholten Aufrufen
- `test_walker_file_as_root_raises_error` NEU: ValueError wenn Root ein File ist
- `test_walker_ignores_directories_only_files` NEU: Nur Dateien, keine Verzeichnisse in Ergebnissen
- 26 Tests total, alle AAA-Pattern mit Docstrings, RED Phase weiterhin aktiv

## Phase 6: FileWalker - TDD GREEN Phase

### #054 - 2025-12-13 16:30
**Aktion:** FileWalker implementiert (TDD GREEN Phase)
**Warum:** Plan 03 erfordert vollständige Implementation basierend auf existierenden Tests
**Ergebnis:**
- `src/codemap/scout/walker.py` NEU:
  - `DEFAULT_IGNORES: set[str] = {".git", ".venv", "__pycache__"}` Konstante
  - `FileWalker` Klasse mit Docstring (Zweck, Pattern-Matching, Rückgabetyp)
  - `walk(root, ignore_patterns=None) -> list[FileEntry]`:
    - Input-Validierung: ValueError für nicht-existente/nicht-Directory Pfade
    - Pattern-Kompilierung mit `pathspec.PathSpec.from_lines("gitwildmatch", ...)`
    - Directory-Traversal mit `root.rglob("*")`
    - Metadata-Collection: `size = path.stat().st_size`, `token_est = size // 4`
    - OSError-Handling für Permission-Errors (graceful skip)
    - Case-insensitive String-Sortierung: `str(e.path).lower()`
- `src/codemap/scout/__init__.py`: `FileWalker` zu Import und `__all__` hinzugefügt
- `tests/unit/scout/test_init.py`: FileWalker in expected exports aufgenommen
- `tests/unit/scout/test_walker.py`:
  - `test_walker_without_ignore_patterns` NEU: Testet optionales `ignore_patterns`
  - Permission-Error-Test-Mock korrigiert (`**kwargs` für `follow_symlinks`)
- 27/27 Walker-Tests bestanden, 100% Coverage für walker.py

### #055 - 2025-12-13 16:45
**Aktion:** Sortierung auf case-insensitive String-Vergleich geändert (Review-Feedback)
**Warum:** Verifikationskommentar: Path-Objekt-Sortierung kann von expliziter String-Sortierung abweichen
**Ergebnis:**
- `walker.py`: `entries.sort(key=lambda e: str(e.path).lower())` statt `e.path`
- Konsistente, case-insensitive alphabetische Sortierung auf allen Plattformen

## Phase 6: FileWalker - TDD REFACTOR Phase

### #057 - 2025-12-13 18:30
**Aktion:** FileWalker Refactoring nach Verifikationskommentaren
**Warum:** Code-Review identifizierte 3 Verbesserungsmöglichkeiten für Konsistenz, Effizienz und Explizitheit
**Ergebnis:**
1. **Case-sensitive Sortierung** (Kommentar 1):
   - `entries.sort(key=lambda e: str(e.path))` statt `.lower()`
   - Konsistent mit TreeGenerator und Dateisystem-Semantik
2. **Early Pruning für DEFAULT_IGNORES** (Kommentar 2):
   - `if any(part in DEFAULT_IGNORES for part in relative_path.parts): continue`
   - Short-circuit vor pathspec-Matching (Set-Lookup O(1) effizienter)
3. **Explizite OSError-Behandlung** (Kommentar 3):
   - Separater try/except für `is_dir()` (kann auch stat aufrufen)
   - Separater try/except für `stat()` Metadata-Collection
   - Relative-Path-Berechnung und pathspec-Matching außerhalb try-Blöcke
- `tests/unit/scout/test_walker.py` ERWEITERT:
  - `test_walker_handles_permission_error` → `test_walker_handles_permission_error_on_is_dir`
  - `test_walker_handles_permission_error_on_stat` NEU (mit Call-Tracking für Metadata-stat)
  - mypy-Fehler behoben: `mock_stat` Signatur korrigiert für `follow_symlinks: bool`
  - `import os` hinzugefügt für `os.stat_result` Type-Annotation
- 28/28 Tests bestanden, 100% Coverage für walker.py, alle Quality-Checks bestanden

### #056 - 2025-12-13 16:50
**Aktion:** ignore_patterns Parameter optional gemacht (Review-Feedback)
**Warum:** Verifikationskommentar: Einfache Nutzung ohne Patterns sollte möglich sein
**Ergebnis:**
- `walk(root, ignore_patterns=None)`: Parameter mit Default `None`
- Interne Normalisierung: `if ignore_patterns is None: ignore_patterns = []`
- Docstring: "Optional list of gitignore-style patterns" mit Default-Hinweis
- `test_walker_without_ignore_patterns` NEU: Verifiziert Aufruf ohne zweiten Parameter
- 27/27 Tests bestanden, 100% Coverage für walker.py

## Phase 7: .gitignore-Unterstützung und erweiterte Default-Ignores

### #058 - 2025-12-13 19:30
**Aktion:** Tests für .gitignore-Unterstützung und polyglot Default-Ignores erstellt (TDD RED Phase)
**Warum:** Plan 01 Phase 7 erfordert Tests vor Implementation für .gitignore-Parsing und erweiterte Ignores
**Ergebnis:**
- `tests/unit/scout/test_walker.py` ERWEITERT (TestFileWalkerDefaultIgnores):
  - `test_walker_reads_local_gitignore` NEU: Testet .gitignore-Datei-Parsing
  - `test_walker_ignores_common_junk_polyglot` NEU: Testet node_modules, wp-admin, .dart_tool, target
- RED Phase verifiziert: Beide Tests fehlgeschlagen wie erwartet
  - gitignore-Test: `local_ignore.txt` erschien in Ergebnissen
  - polyglot-Test: `.dart_tool` erschien in Ergebnissen

### #059 - 2025-12-13 19:45
**Aktion:** .gitignore-Unterstützung in FileWalker implementiert (TDD GREEN Phase - Comment 1)
**Warum:** Test `test_walker_reads_local_gitignore` erforderte .gitignore-Parsing
**Ergebnis:**
- `src/codemap/scout/walker.py` ERWEITERT:
  - `_load_gitignore(root: Path) -> list[str]` NEU: Liest .gitignore aus Root
    - Parst jede Zeile als Pattern (ignoriert # Kommentare und leere Zeilen)
    - OSError-Handling für unlesbare Dateien
  - `walk()` aktualisiert: Lädt und kombiniert .gitignore-Patterns mit DEFAULT_IGNORES
  - Docstring aktualisiert: Beschreibt additive Pattern-Kombination
- 30/30 Tests bestanden, test_walker_reads_local_gitignore GRÜN

### #060 - 2025-12-13 19:50
**Aktion:** DEFAULT_IGNORES um polyglot Verzeichnisse erweitert (TDD GREEN Phase - Comment 2)
**Warum:** Test `test_walker_ignores_common_junk_polyglot` erforderte erweiterte Ignores
**Ergebnis:**
- `src/codemap/scout/walker.py`:
  - `DEFAULT_IGNORES` erweitert: `node_modules`, `wp-admin`, `.dart_tool`, `target`
  - Kommentar: "polyglot defaults for common ecosystems"
- 30/30 Tests bestanden, test_walker_ignores_common_junk_polyglot GRÜN

### #061 - 2025-12-13 20:00
**Aktion:** .gitignore-Semantik dokumentiert (Review-Feedback - Comment 3)
**Warum:** Verifikationskommentar forderte klare Dokumentation der additiven Semantik
**Ergebnis:**
- `src/codemap/scout/walker.py` Docstrings präzisiert:
  - Klassen-Docstring: "Ignore sources (all applied together)" mit 3 nummerierten Punkten
  - Methoden-Docstring: "Exclusion behavior" Abschnitt mit Erklärung
  - Explizit: ".gitignore file is always read from root directory if present, regardless of whether ignore_patterns is provided"
- Entscheidung: Variante 1 gewählt (.gitignore immer additiv angewendet)
- 30/30 Tests bestanden, keine Regressionen

### #062 - 2025-12-13 21:00
**Aktion:** DEFAULT_IGNORES/IGNORED_DIRS auf umfassende polyglot Master-Liste erweitert (Plan Phase 7 Step 1-2)
**Warum:** Plan erforderte konsistente, umfassende Ignore-Liste für beide Module (walker.py, tree.py)
**Ergebnis:**
- `src/codemap/scout/walker.py`: DEFAULT_IGNORES von 7 auf 82 Patterns erweitert
  - 11 Kategorien: System/SCM, Build, Node/Web, Python, PHP/WordPress, Dart/Flutter, Java/JVM, .NET, C/C++, Go, IDEs
  - Kommentierte Gruppierung für Wartbarkeit
- `src/codemap/scout/tree.py`: IGNORED_DIRS identisch aktualisiert (Plan-Anforderung: "identical master lists")
- `tests/unit/scout/test_walker.py`: 7 neue Tests für alle Ecosystem-Kategorien
- `tests/unit/scout/test_tree.py`: 5 neue Tests für Ecosystem-Kategorien
- 116/116 Tests bestanden, 100% Coverage für scout Module

### #063 - 2025-12-13 21:15
**Aktion:** Exception-Handling für .gitignore-Lesen konsistent gemacht (Verifikationskommentar 1)
**Warum:** tree.py fing `(OSError, UnicodeError)`, walker.py nur `OSError`
**Ergebnis:**
- `walker.py` `_load_gitignore()`: `except OSError` → `except (OSError, UnicodeError)`
- Konsistente Fehlerbehandlung in beiden Modulen
- 116/116 Tests bestanden

### #064 - 2025-12-13 21:30
**Aktion:** Wildcard-Pattern `*.egg-info` aus hardcoded Sets entfernt (Verifikationskommentar 2)
**Warum:** `*.egg-info` funktioniert nicht für direkte Namensvergleiche (early pruning, `_should_ignore`)
**Ergebnis:**
- `walker.py`: `*.egg-info` aus DEFAULT_IGNORES entfernt
- `walker.py`: `DEFAULT_PATHSPEC_PATTERNS: list[str]` NEU für Wildcard-Patterns
- `walker.py`: Pattern-Kombination erweitert um DEFAULT_PATHSPEC_PATTERNS (nur via PathSpec angewendet)
- `tree.py`: `*.egg-info` aus IGNORED_DIRS entfernt (war dort ohnehin wirkungslos)
- `test_walker.py`: `test_walker_ignores_egg_info_directories` NEU: Verifiziert Wildcard-Matching via PathSpec
- Architektur-Trennung: Exakte Namen in Sets (für O(1) Lookup), Wildcards in separater Liste (für PathSpec)
- 116/116 Tests bestanden, 100% Coverage für scout Module

### #065 - 2025-12-13 22:00
**Aktion:** HARD_IGNORES für Re-Include-Unterstützung eingeführt (Verifikationskommentar 1)
**Warum:** Frühe DEFAULT_IGNORES-Prüfung verhinderte Re-Includes via .gitignore-Negation (`!dist/keep.txt`)
**Ergebnis:**
- `walker.py`: `HARD_IGNORES: set[str]` NEU mit `.git`, `.venv`, `__pycache__` (nie re-includierbar)
- `walker.py`: Early Pruning nutzt jetzt nur HARD_IGNORES statt DEFAULT_IGNORES
- `walker.py`: DEFAULT_IGNORES gehen vollständig durch PathSpec (unterstützt Negation)
- `walker.py`: Docstring aktualisiert mit 5 Ignore-Quellen (HARD_IGNORES, IGNORED_FILES, DEFAULT_IGNORES, .gitignore, User Patterns)
- `test_walker.py`: `test_walker_allows_reinclude_via_gitignore_negation` NEU: Verifiziert `!dist/keep.txt` Re-Include
- 117/117 Scout-Tests bestanden, 100% Coverage für walker.py

### #066 - 2025-12-13 22:15
**Aktion:** IGNORED_FILES für .gitignore-Ausschluss eingeführt (Verifikationskommentar 2)
**Warum:** TreeGenerator ignorierte .gitignore standardmäßig, FileWalker nicht - Inkonsistenz
**Ergebnis:**
- `walker.py`: `IGNORED_FILES: set[str] = {".gitignore"}` NEU (konsistent mit tree.py)
- `walker.py`: walk() prüft `relative_path.name in IGNORED_FILES` nach HARD_IGNORES
- `walker.py`: Docstring aktualisiert: IGNORED_FILES als zweite Ignore-Quelle dokumentiert
- `test_walker.py`: `test_walker_excludes_gitignore_file` NEU: Verifiziert .gitignore-Ausschluss
- Konsistenz erreicht: Beide Module (tree.py, walker.py) behandeln .gitignore identisch
- 118/118 Scout-Tests bestanden, 100% Coverage für walker.py

## Phase 8: Mapper Module - TDD RED Phase

### #067 - 2025-12-13 23:30
**Aktion:** TDD RED Phase Tests für Mapper Module erstellt
**Warum:** Plan erfordert tree-sitter-basierte Code-Analyse; strikte TDD mit Tests vor Implementation
**Ergebnis:**
- `tests/unit/mapper/__init__.py` NEU: Package-Marker
- `tests/unit/mapper/test_models.py` NEU: 5 Tests für CodeNode Dataclass
  - Creation, Immutability (frozen), Equality, Attributes, Different Types
- `tests/unit/mapper/test_reader.py` NEU: 5 Tests für ContentReader
  - UTF-8, Latin-1 Fallback, Nonexistent File, Binary File, Empty File
  - API: `read_file()` (nicht `read()`) per Plan-Spezifikation
- `tests/unit/mapper/test_engine.py` NEU: 8 Tests für ParserEngine
  - TestLanguageMapping (2): .py → "python", unknown → ValueError
  - TestParserEngine (6): Function, Class, Import, From-Import, Multiple, Empty
  - From-Import-Verhalten dokumentiert: `name` = Modul-Teil (X bei `from X import Y`)
- RED Phase verifiziert: Alle 18 Tests schlagen mit `ModuleNotFoundError: No module named 'codemap.mapper'` fehl
- Branch: `feature/mapper-tdd-red-phase`

## Phase 8: Mapper Module - TDD GREEN Phase

### #068 - 2025-12-13 14:00
**Aktion:** TDD GREEN Phase - Mapper Module vollständig implementiert
**Warum:** Plan 02 erfordert Implementation aller vier Module (models, reader, queries, engine)
**Ergebnis:**
- `src/codemap/mapper/__init__.py` NEU: Package mit Public API Exports
- `src/codemap/mapper/models.py` NEU: `CodeNode` frozen Dataclass (type, name, start_line, end_line)
- `src/codemap/mapper/reader.py` NEU: `ContentReader` mit UTF-8/Latin-1 Fallback, Binary-Detection
- `src/codemap/mapper/queries.py` NEU: Tree-sitter S-Expression Queries für Python
- `src/codemap/mapper/engine.py` NEU: `ParserEngine` mit tree-sitter-language-pack Integration
- Test hinzugefügt: `test_unsupported_language_raises_error` für 100% Coverage
- 19/19 Tests bestanden, 100% Coverage für alle Mapper-Module, mypy clean

### #069 - 2025-12-13 14:30
**Aktion:** tree-sitter API-Nutzung refactored (Verifikationskommentar 1)
**Warum:** QueryCursor API war inkorrekt, sollte `(node, capture_name)` Tupel-Iteration nutzen
**Ergebnis:**
- `engine.py`: `_flatten_captures()` Hilfsmethode hinzugefügt
- `engine.py`: `Query(lang, ...)` + `QueryCursor(query)` + `cursor.captures(root_node)`
- `engine.py`: Iteration über `(ts_node, capture_name)` Tupel mit `capture_to_type` Mapping
- 19/19 Tests bestanden, 100% Coverage

### #070 - 2025-12-13 15:00
**Aktion:** OSError-Handling in ContentReader hinzugefügt (Verifikationskommentar 2)
**Warum:** `path.read_bytes()` konnte bei Permission-Fehlern unerwartete Exceptions werfen
**Ergebnis:**
- `reader.py`: try/except um `path.read_bytes()`, wrapped `OSError` in `ContentReadError`
- `reader.py`: Docstring aktualisiert um Permission-Denied-Fälle
- `test_reader.py`: `test_read_permission_error_raises_content_read_error` NEU (mit Mock)
- 20/20 Tests bestanden, 100% Coverage für reader.py

### #071 - 2025-12-13 15:15
**Aktion:** get_language_id API von String auf Path umgestellt (Verifikationskommentar 3)
**Warum:** Produktionscode hat typischerweise Path-Objekte, nicht Extensions-Strings
**Ergebnis:**
- `engine.py`: `get_language_id(extension: str)` → `get_language_id(path: Path)`
- `engine.py`: Extrahiert Extension intern via `path.suffix.lower()`
- `test_engine.py`: Tests aktualisiert: `Path("example.py")` statt `".py"`
- 20/20 Tests bestanden, 100% Coverage
