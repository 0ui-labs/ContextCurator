import asyncio
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Pfad-Setup
sys.path.append(str(Path.cwd() / "src"))

try:
    from codemap.engine import MapBuilder, GraphEnricher
    from codemap.core.llm import get_provider
except ImportError as e:
    print(f"❌ Import Fehler: {e}")
    sys.exit(1)

async def main():
    root_path = Path.cwd() / "src"
    print(f"🚀 Starte Semantic Enrichment Demo für: {root_path}")
    print("=" * 60)

    # 1. Graph bauen
    print("\n1️⃣  Baue strukturellen Graphen (Skelett)...")
    builder = MapBuilder()
    t0 = time.time()
    graph_manager = builder.build(root_path)
    print(f"   ✅ Graph gebaut in {time.time() - t0:.2f}s")
    
    # Statistiken vor Enrichment
    stats = graph_manager.graph_stats
    print(f"   Nodes: {stats['nodes']}, Edges: {stats['edges']}")

    # 2. KI Provider laden
    print("\n2️⃣  Initialisiere KI (Cerebras)...")
    try:
        # Versuche Cerebras, Fallback auf Mock
        try:
            provider = get_provider("cerebras")
            print("   🤖 Nutze Cerebras Llama 3.3 70B (High Speed)")
        except ValueError:
            print("   ⚠️  Kein API Key. Nutze Mock-Provider (Simulation).")
            provider = get_provider("mock")
            
        enricher = GraphEnricher(graph_manager, provider)
        
    except Exception as e:
        print(f"💥 Fehler beim Provider-Init: {e}")
        return

    # 3. Enrichment starten (Der Turbo)
    print("\n3️⃣  Starte KI-Analyse (Parallel Batches)...")
    t1 = time.time()
    
    # Batch size 10 ist gut für Cerebras
    await enricher.enrich_nodes(batch_size=10)
    
    duration = time.time() - t1
    print(f"   ✅ Analyse fertig in {duration:.2f}s")

    # 4. Ergebnisse anzeigen
    print("\n📋 ERGEBNISSE (Was die KI über deinen Code denkt):")
    print("=" * 60)
    
    graph = graph_manager.graph
    count = 0
    
    for node_id, attrs in graph.nodes(data=True):
        # Zeige nur Funktionen/Klassen, die enriched wurden
        if attrs.get("type") in ["function", "class"] and "summary" in attrs:
            count += 1
            if count > 5: break # Nur die ersten 5 zeigen
            
            print(f"\n🔹 {node_id}")
            print(f"   📝 Summary: {attrs['summary']}")
            if attrs.get("risks"):
                print(f"   ⚠️  Risks:   {attrs['risks'][0]}") # Nur erstes Risiko
                if len(attrs['risks']) > 1:
                    print(f"               (+ {len(attrs['risks'])-1} weitere)")

    print("-" * 60)
    print(f"Gescannte Code-Knoten: {count} (Demo limitiert Anzeige auf 5)")

if __name__ == "__main__":
    asyncio.run(main())