I have created the following plan after thorough exploration and analysis of the codebase. Follow the below plan verbatim. Trust the files and references. Do not re-verify what's written in the plan. Explore only when absolutely necessary. First implement all the proposed file changes and then I'll review all the changes together at the end.

## Beobachtungen

Das Projekt folgt strikten TDD-Prinzipien mit 100% Coverage-Anforderung. Der Code verwendet frozen dataclasses für Immutabilität, umfassende Docstrings mit Beispielen, strikte Type Hints (mypy strict mode) und klare Separation of Concerns. Das `core`-Modul ist aktuell leer. Die `scout`-Module zeigen etablierte Patterns: Protocol-basierte Abstraktion wird neu eingeführt, Dependency Injection über `__init__`, und robuste Error-Handling-Strategien.

## Ansatz

Implementierung eines Protocol-basierten LLM-Provider-Interfaces mit Factory-Pattern für flexible Provider-Auswahl. Der `MockProvider` ermöglicht schnelle, deterministische Tests ohne externe Abhängigkeiten. Der `CerebrasProvider`-Stub bereitet die spätere Integration vor, ohne die aktuelle Phase zu blockieren. Die Factory-Funktion `get_provider()` entkoppelt Consumer-Code von konkreten Implementierungen und ermöglicht einfaches Testen und spätere Erweiterungen.

## Implementierungsschritte

### 1. LLMProvider Protocol Definition

Erstelle `file:src/codemap/core/llm.py`:

**Protocol Interface:**
- Importiere `Protocol` aus `typing` (Python 3.11+)
- Definiere `LLMProvider(Protocol)` mit Methode `send(system: str, user: str) -> str`
- Füge umfassenden Docstring hinzu mit Beschreibung des Contracts
- Dokumentiere Parameter: `system` (System-Prompt für Kontext), `user` (User-Prompt mit Anfrage)
- Dokumentiere Return: String-Antwort vom LLM

**Docstring-Struktur:**
```
"""LLM Provider Protocol für einheitliche KI-Anbindung.

Definiert das Interface für alle LLM-Provider-Implementierungen.
Ermöglicht Dependency Injection und einfaches Testen mit Mocks.

Methods:
    send: Sendet System- und User-Prompts an LLM, gibt Antwort zurück.
"""
```

### 2. MockProvider Implementierung

Im selben File `file:src/codemap/core/llm.py`:

**Klasse MockProvider:**
- Implementiere `send(system: str, user: str) -> str` Methode
- Rückgabewert: Einfacher deterministischer String für Tests (z.B. `"node_modules/\ndist/\n.venv/"`)
- Füge `__init__()` hinzu (leer, für Konsistenz)
- Docstring: Beschreibe Zweck als Test-Double für deterministische Tests
- Erwähne, dass echte LLM-Calls vermieden werden

**Implementierungsdetails:**
- Keine externe Abhängigkeiten
- Keine State-Verwaltung notwendig
- Return-Wert sollte gitignore-Format simulieren (für spätere StructureAdvisor-Tests)

### 3. CerebrasProvider Stub

Im selben File `file:src/codemap/core/llm.py`:

**Klasse CerebrasProvider:**
- Implementiere `send(system: str, user: str) -> str` Methode
- Methode wirft `NotImplementedError` mit Message: `"CerebrasProvider not yet implemented"`
- Füge `__init__()` hinzu (leer oder mit Platzhalter-Parametern für API-Key)
- Docstring: Markiere als Stub für zukünftige Cerebras-Integration
- Erwähne, dass dies Vorbereitung für echte API-Anbindung ist

**Coverage-Hinweis:**
- `NotImplementedError` ist in `pyproject.toml` Coverage-Ausnahme (Zeile 51)
- Stub wird nicht die Coverage beeinträchtigen

### 4. Factory-Funktion get_provider

Im selben File `file:src/codemap/core/llm.py`:

**Funktion get_provider:**
- Signatur: `get_provider(name: str = "mock") -> LLMProvider`
- Logik:
  - Wenn `name == "mock"`: Return `MockProvider()`
  - Wenn `name == "cerebras"`: Return `CerebrasProvider()`
  - Sonst: Raise `ValueError` mit Message: `f"Unknown provider: {name}"`
- Docstring: Beschreibe Factory-Pattern, verfügbare Provider, Default-Verhalten
- Füge Examples-Section hinzu mit Mock- und Cerebras-Beispielen

**Type Safety:**
- Return-Type ist `LLMProvider` Protocol
- Ermöglicht Type-Checking für alle Consumer

### 5. Module Exports aktualisieren

Aktualisiere `file:src/codemap/core/__init__.py`:

**Änderungen:**
- Importiere: `from codemap.core.llm import LLMProvider, MockProvider, CerebrasProvider, get_provider`
- Aktualisiere `__all__`: `["LLMProvider", "MockProvider", "CerebrasProvider", "get_provider"]`
- Behalte existierenden Docstring bei
- Erweitere Docstring um Beschreibung der LLM-Provider-Funktionalität

**Struktur:**
```python
"""Core module for Codemap.

This module provides the core functionality for code mapping and analysis,
including LLM provider abstractions for AI-powered analysis.
"""

from codemap.core.llm import CerebrasProvider, LLMProvider, MockProvider, get_provider

__all__ = ["LLMProvider", "MockProvider", "CerebrasProvider", "get_provider"]
```

### 6. Type Checking und Code Quality

**Mypy Compliance:**
- Alle Funktionen und Methoden mit vollständigen Type Hints
- Protocol-Konformität wird automatisch von mypy geprüft
- Keine `type: ignore` Kommentare notwendig

**Ruff Compliance:**
- Imports alphabetisch sortiert (I-Regel)
- Line length max 100 Zeichen
- Naming conventions (N-Regel): PascalCase für Klassen, snake_case für Funktionen

**Docstring Standards:**
- Google-Style Docstrings
- Alle öffentlichen Klassen, Methoden und Funktionen dokumentiert
- Examples wo sinnvoll (besonders bei Factory-Funktion)

## Dateistruktur

```
src/codemap/core/
├── __init__.py          # Aktualisiert mit LLM-Exports
└── llm.py              # NEU: Protocol, Implementierungen, Factory
```

## Abhängigkeiten

Keine neuen Dependencies erforderlich. Alle Implementierungen nutzen Python Standard Library:
- `typing.Protocol` (Python 3.11+)
- Built-in Exception-Typen

## Nächste Schritte (für andere Engineers)

Nach dieser Phase können Tests in `file:tests/unit/core/test_llm.py` erstellt werden, die:
- Protocol-Konformität verifizieren
- MockProvider-Verhalten testen
- Factory-Funktion mit allen Providern testen
- CerebrasProvider NotImplementedError verifizieren
- Type-Checking-Kompatibilität sicherstellen