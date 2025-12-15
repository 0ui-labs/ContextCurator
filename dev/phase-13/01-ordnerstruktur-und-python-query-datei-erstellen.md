I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Beobachtungen

Die aktuelle Codebasis verwendet `PYTHON_ALL_QUERY` aus `file:src/codemap/mapper/queries.py` (Zeilen 36-48), die in `LANGUAGE_QUERIES` Dictionary in `file:src/codemap/mapper/engine.py` referenziert wird. Das Projekt nutzt Python 3.11+ mit setuptools und hat strikte TDD-Anforderungen (100% Coverage). Es existiert noch kein Mechanismus für Resource-Loading oder Package-Data-Konfiguration.

## Ansatz

Wir erstellen eine neue Verzeichnisstruktur `src/codemap/mapper/languages/` als Python-Package mit `__init__.py`, um Kompatibilität mit `importlib.resources` sicherzustellen. Die Python Tree-sitter Query wird aus `queries.py` in eine dedizierte `.scm`-Datei extrahiert. Dies ist die Grundlage für das spätere dynamische Query-Loading in den GREEN/REFACTOR Phasen.

## Implementierungsschritte

### 1. Verzeichnisstruktur erstellen

Erstelle das Verzeichnis `src/codemap/mapper/languages/`:

```bash
mkdir -p src/codemap/mapper/languages
```

**Rationale**: Dieses Verzeichnis wird alle sprachspezifischen Tree-sitter Query-Dateien enthalten und folgt der Konvention `languages/{language}.scm`.

### 2. Python-Package initialisieren

Erstelle leere Datei `file:src/codemap/mapper/languages/__init__.py`:

```bash
touch src/codemap/mapper/languages/__init__.py
```

**Rationale**: 
- Macht `languages/` zu einem echten Python-Package
- Ermöglicht zuverlässige Nutzung von `importlib.resources.files()` in Python 3.11+
- Stellt sicher, dass setuptools das Verzeichnis als Teil des Packages erkennt
- Notwendig für spätere Package-Distribution (pip install)

### 3. Python Query-Datei erstellen

Erstelle `file:src/codemap/mapper/languages/python.scm` mit folgendem Inhalt (extrahiert aus `PYTHON_ALL_QUERY` in `file:src/codemap/mapper/queries.py`, Zeilen 36-48):

```scheme
(function_definition
  name: (identifier) @function.name)

(class_definition
  name: (identifier) @class.name)

(import_statement
  name: (dotted_name) @import.name)

(import_from_statement
  module_name: (dotted_name) @import.module)
```

**Wichtig**: 
- Keine führenden/trailing Leerzeilen
- Exakte Kopie des Query-Strings ohne die umschließenden Triple-Quotes
- Dateiname folgt dem Pattern `{language_id}.scm` (hier: `python.scm`)

### 4. Verzeichnisstruktur verifizieren

Nach der Erstellung sollte die Struktur wie folgt aussehen:

```
src/codemap/mapper/
├── __init__.py
├── engine.py
├── models.py
├── queries.py
├── reader.py
└── languages/
    ├── __init__.py
    └── python.scm
```

**Verifikation**:
```bash
ls -la src/codemap/mapper/languages/
# Erwartete Ausgabe:
# __init__.py
# python.scm
```

### 5. Package-Data-Konfiguration vorbereiten (Optional für Phase 1)

**Hinweis für spätere Phasen**: Um `.scm`-Dateien in der Package-Distribution einzuschließen, muss in `file:pyproject.toml` folgendes ergänzt werden:

```toml
[tool.setuptools.package-data]
"codemap.mapper.languages" = ["*.scm"]
```

**Für Phase 1**: Diese Konfiguration ist noch nicht erforderlich, da wir nur die Dateistruktur erstellen. Die Konfiguration wird relevant, wenn das dynamische Loading in der GREEN Phase implementiert wird.

## Zusammenfassung

| Aktion | Datei/Verzeichnis | Status |
|--------|-------------------|--------|
| Verzeichnis erstellen | `src/codemap/mapper/languages/` | ✓ Neu |
| Package-Marker | `src/codemap/mapper/languages/__init__.py` | ✓ Neu (leer) |
| Query-Datei | `src/codemap/mapper/languages/python.scm` | ✓ Neu (Query-Inhalt) |

**Nächste Schritte** (für andere Engineers):
- RED Phase: Tests für `_load_query_from_file()` erstellen
- GREEN Phase: Dynamisches Loading mit `importlib.resources` implementieren
- REFACTOR Phase: `LANGUAGE_QUERIES` Dictionary entfernen