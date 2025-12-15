import asyncio
import sys
import time
from pathlib import Path

# Pfad-Setup für Imports
sys.path.append(str(Path.cwd() / "src"))

try:
    from codemap.scout import TreeGenerator, FileWalker, StructureAdvisor
    from codemap.core.llm import get_provider
except ImportError as e:
    print(f"❌ Import Fehler: {e}")
    sys.exit(1)


async def run_analysis(report, advisor):
    """Async wrapper for advisor.analyze() to enable await usage."""
    return await advisor.analyze(report)


def format_size(size_bytes):
    """Hilfsfunktion für lesbare Dateigrößen."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def main():
    root = Path.cwd()
    print(f"🚀 Starte Full Context Scan für: {root.name}")
    print("=" * 60)

    # ---------------------------------------------------------
    # SCHRITT 1: Die Struktur verstehen (Der Scout)
    # ---------------------------------------------------------
    print("\n1️⃣  Erstelle visuelle Code-Map...")
    t0 = time.time()
    
    tree_gen = TreeGenerator()
    try:
        report = tree_gen.generate(root)
    except Exception as e:
        print(f"💥 Fehler beim Tree-Scan: {e}")
        sys.exit(1)
        
    print(f"   ✅ Fertig in {time.time() - t0:.3f}s")
    print(f"   ℹ️  Gefunden: {report.total_files} Dateien in {report.total_folders} Ordnern")

    # ---------------------------------------------------------
    # SCHRITT 2: Die Relevanz bewerten (Der Advisor)
    # ---------------------------------------------------------
    print("\n2️⃣  Befrage KI nach Irrelevanz (Ignore-Patterns)...")
    
    try:
        # Wir versuchen Cerebras, fallen aber auf Mock zurück wenn kein Key da ist
        try:
            provider = get_provider("cerebras")
            print("   🤖 Nutze Cerebras (Llama 3.3 70B)")
        except ValueError:
            print("   ⚠️  Kein CEREBRAS_API_KEY gefunden. Nutze Mock-Provider (Simulation).")
            provider = get_provider("mock")
            
        advisor = StructureAdvisor(provider)
        t1 = time.time()
        patterns = asyncio.run(run_analysis(report, advisor))

    except Exception as e:
        print(f"💥 Fehler bei der KI-Analyse: {e}")
        sys.exit(1)

    print(f"   ✅ Analyse fertig in {time.time() - t1:.3f}s")
    print(f"   📋 KI empfiehlt {len(patterns)} Patterns zum Ignorieren:")
    for p in patterns[:5]: # Zeige nur die ersten 5
        print(f"      - {p}")
    if len(patterns) > 5:
        print(f"      - ... und {len(patterns)-5} weitere")

    # ---------------------------------------------------------
    # SCHRITT 3: Die Inventur (Der Walker)
    # ---------------------------------------------------------
    print("\n3️⃣  Erstelle finales Datei-Inventar...")
    t2 = time.time()
    
    walker = FileWalker()
    try:
        # Hier passiert die Magie: KI-Patterns werden angewendet
        inventory = walker.walk(root, ignore_patterns=patterns)
    except Exception as e:
        print(f"💥 Fehler beim File-Walk: {e}")
        sys.exit(1)

    duration_walk = time.time() - t2
    
    # ---------------------------------------------------------
    # ERGEBNIS
    # ---------------------------------------------------------
    total_size = sum(f.size for f in inventory)
    total_tokens = sum(f.token_est for f in inventory)
    
    print("\n" + "=" * 60)
    print("📊 ERGEBNIS DES KONTEXT-SCANS")
    print("=" * 60)
    print(f"✅ Relevante Dateien:  {len(inventory)}")
    print(f"💾 Gesamtgröße:        {format_size(total_size)}")
    print(f"🧮 Geschätzte Token:   ~{total_tokens:,}")
    print(f"⏱️  Gesamtdauer:        {time.time() - t0:.3f}s")
    print("-" * 60)
    
    print("\nAuswahl der relevantesten Dateien (Top 10):")
    # Zeige die ersten 10 Dateien (alphabetisch sortiert durch Walker)
    for entry in inventory[:10]:
        print(f"📄 {entry.path} ({format_size(entry.size)})")
        
    if len(inventory) > 10:
        print(f"... und {len(inventory) - 10} weitere.")

if __name__ == "__main__":
    main()