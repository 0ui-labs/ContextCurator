# ContextCurator - Projekt Roadmap

> **Vision:** Ein hierarchisches, semantisches Code-Verzeichnis, das wie Google Maps funktioniert.
> Ein spezialisierter Agent kann "reinzoomen" und Implementierungspläne auf Sicherheit und
> Sinnhaftigkeit prüfen, bevor Code geschrieben wird.

---

## Aktueller Stand (Phase 1-16 abgeschlossen)

| Komponente | Status | Beschreibung |
|------------|--------|--------------|
| FileWalker | ✅ | Findet Dateien, respektiert .gitignore |
| ParserEngine | ✅ | Extrahiert Code-Struktur via tree-sitter |
| GraphManager | ✅ | NetworkX-Graph mit Nodes/Edges |
| MapBuilder | ✅ | Orchestriert Build-Prozess |
| Import-Resolution | ✅ | Interne + externe Dependencies |
| LLM Provider | ✅ | Async mit Cerebras/OpenAI-kompatibel |
| GraphEnricher | ⚠️ | Existiert, aber ohne Code-Content |

---

## Phase 17: Code-Content Integration

**Ziel:** Enricher bekommt echten Quellcode, nicht nur Metadaten.

### Aufgaben

1. **ContentReader in Enricher integrieren**
   - GraphEnricher erhält Zugriff auf Dateiinhalte
   - Code zwischen `start_line` und `end_line` extrahieren
   - Token-Limit pro Batch beachten

2. **Prompt-Template erweitern**
   - Code-Snippet im Prompt mitschicken
   - Strukturierte Analyse: Summary, Risks, Dependencies

3. **Graph-Attribute erweitern**
   - `summary`: KI-generierte Beschreibung
   - `risks`: Potenzielle Probleme
   - `touches`: Welche externen Ressourcen (DB, API, Files)

### Akzeptanzkriterien
- [ ] Enricher sendet echten Code an LLM
- [ ] Summaries basieren auf Code-Inhalt, nicht nur Namen
- [ ] 100% Test-Coverage bleibt erhalten

---

## Phase 18: Hierarchische Aggregation

**Ziel:** Zoom-Level Struktur aufbauen (Projekt → Package → Modul → Funktion).

### Aufgaben

1. **Level-Struktur definieren**
   ```
   Level 0: Projekt-Übersicht
   Level 1: Package/Verzeichnis-Ebene
   Level 2: Modul/Datei-Ebene
   Level 3: Klasse/Funktion-Ebene
   Level 4: Code-Detail (Raw Source)
   ```

2. **Aggregations-Nodes im Graph**
   - Package-Nodes mit aggregierten Summaries
   - "Dieses Package enthält Auth, Session, OAuth..."
   - Automatische Generierung aus Kind-Nodes

3. **Summary-Propagation**
   - Bottom-up: Funktions-Summaries → Modul-Summary
   - KI aggregiert: "Was macht dieses Modul insgesamt?"

### Akzeptanzkriterien
- [ ] Graph hat hierarchische Struktur
- [ ] Jedes Level hat eigene Summary
- [ ] Navigation von Level 0 → Level 4 möglich

---

## Phase 19: Inkrementelles Graph-Update

**Ziel:** Nur geänderte Dateien re-analysieren, nicht kompletter Rebuild.

### Aufgaben

1. **Change-Detection**
   - Git-Diff auswerten: Welche Dateien geändert?
   - Neue Dateien erkennen
   - Gelöschte Dateien erkennen

2. **Inkrementeller Graph-Update**
   - Geänderte Nodes updaten (nicht löschen + neu erstellen)
   - Edges neu berechnen bei Import-Änderungen
   - Gelöschte Dateien: Nodes + Edges entfernen

3. **Re-Aggregation**
   - Betroffene Parent-Nodes (Package-Level) neu aggregieren
   - Nur relevante Hierarchie-Pfade updaten

### Akzeptanzkriterien
- [ ] Inkrementelles Update funktioniert
- [ ] Performance: Update schneller als Full-Rebuild
- [ ] Graph-Konsistenz nach Update gewährleistet

---

## Phase 20: Git-Hook Integration

**Ziel:** Automatische Map-Aktualisierung nach jedem Commit.

### Aufgaben

1. **Post-Commit Hook**
   - Shell-Script für `.git/hooks/post-commit`
   - Ruft ContextCurator Update auf
   - Non-blocking (async im Hintergrund)

2. **CLI Command: `curator update`**
   - Erkennt Git-Repo Root
   - Führt inkrementelles Update durch
   - Gibt Status aus (X Dateien aktualisiert)

3. **Hook-Installer**
   - `curator install-hook` Command
   - Installiert Post-Commit Hook automatisch
   - Idempotent (mehrfach ausführbar)

### Akzeptanzkriterien
- [ ] Hook wird bei Commit automatisch ausgeführt
- [ ] Map ist nach Commit aktuell
- [ ] User muss nichts manuell tun

---

## Phase 21: Plan-Analyzer Agent

**Ziel:** Agent kann Implementierungspläne analysieren und auf Risiken prüfen.

### Aufgaben

1. **Plan-Parser**
   - Strukturierten Plan verstehen (Markdown/JSON)
   - Extrahieren: Welche Dateien werden angefasst?
   - Extrahieren: Welche Änderungen geplant?

2. **Impact-Analysis**
   - Graph traversieren: Was hängt von betroffenen Dateien ab?
   - Transitive Dependencies finden
   - "Blast Radius" berechnen

3. **Risk-Detection**
   - Pattern-Matching für bekannte Risiken
   - "Diese Datei wird von 15 anderen importiert"
   - "Diese Funktion hat Side-Effects auf DB"

4. **Angepassten Plan generieren**
   - Warnungen hinzufügen
   - Alternative Vorschläge
   - Begründungen

### Akzeptanzkriterien
- [ ] Plan kann geparst werden
- [ ] Abhängigkeiten werden gefunden
- [ ] Risiken werden identifiziert
- [ ] Angepasster Plan wird generiert

---

## Phase 22: Context-Packager

**Ziel:** Need-to-Know Kontext-Paket für Claude Code schnüren.

### Aufgaben

1. **Relevanz-Bestimmung**
   - Welche Dateien sind für den Plan relevant?
   - Welche Zoom-Level werden gebraucht?
   - Minimaler Kontext für die Aufgabe

2. **Context-Bundle erstellen**
   ```
   {
     "plan_feedback": "...",
     "warnings": [...],
     "context_files": [
       {"path": "auth/session.py", "lines": "45-78", "reason": "..."},
       ...
     ],
     "dependency_graph_excerpt": {...}
   }
   ```

3. **Token-Budget beachten**
   - Kontext auf Token-Limit optimieren
   - Wichtigstes zuerst
   - Zusammenfassungen statt Full-Code wo möglich

### Akzeptanzkriterien
- [ ] Context-Bundle wird generiert
- [ ] Nur relevanter Kontext enthalten
- [ ] Token-Budget wird eingehalten

---

## Phase 23: CLI Interface

**Ziel:** Command-Line Tool für ContextCurator.

### Aufgaben

1. **Basis-Commands**
   ```bash
   curator init          # Initialer Full-Scan
   curator update        # Inkrementelles Update
   curator status        # Map-Statistiken
   curator install-hook  # Git-Hook installieren
   ```

2. **Query-Commands**
   ```bash
   curator show <path>           # Zoom auf Datei/Modul
   curator deps <path>           # Zeige Dependencies
   curator impact <path>         # Was hängt davon ab?
   ```

3. **Plan-Check Command**
   ```bash
   curator check-plan <plan.md>  # Plan analysieren
   curator check-plan --stdin    # Plan von stdin
   ```

### Akzeptanzkriterien
- [ ] CLI installierbar via pip
- [ ] Alle Commands funktionieren
- [ ] Hilfe-Texte vorhanden

---

## Phase 24: MCP Server Integration

**Ziel:** ContextCurator als MCP-Server für Claude Code.

### Aufgaben

1. **MCP Server implementieren**
   - FastMCP oder MCP SDK
   - Tools: `check_plan`, `get_context`, `show_deps`

2. **Tool-Definitionen**
   ```python
   @mcp.tool()
   def check_plan(plan: str) -> PlanFeedback:
       """Prüft einen Implementierungsplan auf Risiken."""

   @mcp.tool()
   def get_context(paths: list[str], depth: int) -> ContextBundle:
       """Holt relevanten Kontext für Dateien."""

   @mcp.tool()
   def show_dependencies(path: str) -> DependencyGraph:
       """Zeigt Abhängigkeiten einer Datei."""
   ```

3. **Claude Code Integration**
   - MCP-Config für Claude Code
   - Dokumentation für Setup

### Akzeptanzkriterien
- [ ] MCP Server läuft
- [ ] Claude Code kann Tools aufrufen
- [ ] Plan-Check funktioniert end-to-end

---

## Phase 25: Polish & Documentation

**Ziel:** Produktionsreife und Dokumentation.

### Aufgaben

1. **Error-Handling**
   - Graceful Degradation bei LLM-Fehlern
   - Fallbacks wenn Map nicht aktuell

2. **Performance-Optimierung**
   - Caching-Strategien
   - Parallel Processing wo möglich

3. **Dokumentation**
   - README mit Quick-Start
   - Architektur-Dokumentation
   - API-Referenz

4. **Beispiel-Workflows**
   - Demo-Videos/GIFs
   - Beispiel-Projekte

### Akzeptanzkriterien
- [ ] Stabil unter Last
- [ ] Dokumentation vollständig
- [ ] Einfaches Onboarding möglich

---

## Zusammenfassung

| Phase | Name | Abhängigkeit | Aufwand |
|-------|------|--------------|---------|
| 17 | Code-Content Integration | - | 🟡 Mittel |
| 18 | Hierarchische Aggregation | Phase 17 | 🔴 Hoch |
| 19 | Inkrementelles Update | Phase 18 | 🟡 Mittel |
| 20 | Git-Hook Integration | Phase 19 | 🟢 Gering |
| 21 | Plan-Analyzer Agent | Phase 18 | 🔴 Hoch |
| 22 | Context-Packager | Phase 21 | 🟡 Mittel |
| 23 | CLI Interface | Phase 19, 21 | 🟡 Mittel |
| 24 | MCP Server | Phase 22, 23 | 🟡 Mittel |
| 25 | Polish & Docs | Alle | 🟡 Mittel |

**Kritischer Pfad:** 17 → 18 → 21 → 22 → 24

---

## Nächster Schritt

**Phase 17 starten:** Enricher mit echtem Code-Content ausstatten.

Dies ist die Grundlage für alles Weitere - ohne echte Code-Analyse sind die Summaries bedeutungslos.
