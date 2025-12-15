import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Wir fügen 'src' zum Python-Pfad hinzu, damit er unser Modul findet
sys.path.append(str(Path.cwd() / "src"))

try:
    from codemap.scout import TreeGenerator
    from codemap.scout.advisor import StructureAdvisor
    from codemap.core.llm import get_provider
except ImportError as e:
    print("Fehler: Konnte 'codemap' nicht importieren.")
    print(f"Details: {e}")
    sys.exit(1)


def main():
    # 1. Start
    root_path = Path.cwd()
    print(f"🚀 Starte StructureAdvisor im Ordner: {root_path.name}")
    print("-" * 50)

    # 2. Tree-Generierung
    print("📂 Scanne Verzeichnisstruktur...")
    generator = TreeGenerator()

    start_time = time.time()

    try:
        report = generator.generate(root_path)
    except Exception as e:
        print(f"💥 Kritischer Fehler beim Scannen: {e}")
        sys.exit(1)

    scan_duration = time.time() - start_time
    print(f"✅ Scan abgeschlossen in {scan_duration:.4f} Sekunden")
    print(f"   Dateien: {report.total_files}, Ordner: {report.total_folders}")
    print("-" * 50)

    # 3. LLM-Provider initialisieren
    print("🤖 Initialisiere Cerebras LLM Provider...")
    try:
        provider = get_provider("cerebras")
        advisor = StructureAdvisor(provider)
    except ValueError as e:
        print(f"❌ Fehler: {e}")
        print("💡 Tipp: Setze die Umgebungsvariable CEREBRAS_API_KEY")
        print("   export CEREBRAS_API_KEY='your-api-key-here'")
        sys.exit(1)

    print("✅ Provider initialisiert")
    print("-" * 50)

    # 4. Analyse durchführen
    print("🔍 Analysiere Struktur mit LLM...")
    analysis_start = time.time()

    try:
        patterns = asyncio.run(advisor.analyze(report))
    except Exception as e:
        print(f"💥 Fehler bei der Analyse: {e}")
        sys.exit(1)

    analysis_duration = time.time() - analysis_start
    print(f"✅ Analyse abgeschlossen in {analysis_duration:.4f} Sekunden")
    print("-" * 50)

    # 5. Ergebnisse ausgeben
    print("📋 VORGESCHLAGENE .GITIGNORE PATTERNS:")
    print()

    if patterns:
        for pattern in patterns:
            print(f"   {pattern}")
    else:
        print("   (Keine Vorschläge - Struktur ist bereits optimal)")

    print()
    print("-" * 50)
    print("📊 ZUSAMMENFASSUNG:")
    print(f"   Gescannte Dateien:     {report.total_files}")
    print(f"   Gescannte Ordner:      {report.total_folders}")
    print(f"   Gefundene Patterns:    {len(patterns)}")
    print(f"   Scan-Dauer:            {scan_duration:.4f} Sekunden")
    print(f"   Analyse-Dauer:         {analysis_duration:.4f} Sekunden")
    print(f"   Gesamt-Dauer:          {(scan_duration + analysis_duration):.4f} Sekunden")
    print("-" * 50)


if __name__ == "__main__":
    main()
