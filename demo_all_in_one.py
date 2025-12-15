import asyncio
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Environment Variablen laden (für CEREBRAS_API_KEY)
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
    root_path = Path.cwd() / "src"  # Wir scannen src für korrekte Imports
    print("=" * 80)
    print(f"🚀 ContextCurator: DEEP DIVE ANALYSE")
    print(f"📂 Ziel: {root_path}")
    print("=" * 80)

    # ---------------------------------------------------------
    # SCHRITT 1: Struktur & Map Builder
    # ---------------------------------------------------------
    print("\n1️⃣  PHASE 1: STRUKTUR-SCAN (MapBuilder)")
    print("-" * 80)
    
    t0 = time.time()
    builder = MapBuilder()
    
    # Graph bauen (Scout + Mapper + GraphManager in einem)
    graph_manager = builder.build(root_path)
    graph = graph_manager.graph
    
    duration_build = time.time() - t0
    print(f"✅ Graph gebaut in {duration_build:.3f}s")
    
    # --- UNFILTERED FILE LIST ---
    print("\n📄 Gefundene Dateien (Vollständige Inventur):")
    file_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "file"]
    file_nodes.sort()
    
    for i, f in enumerate(file_nodes, 1):
        print(f"   {i:03d}. {f}")
    
    print(f"\n   -> Gesamt: {len(file_nodes)} Dateien.")

    # ---------------------------------------------------------
    # SCHRITT 2: KI-Analyse (Enricher)
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("2️⃣  PHASE 2: SEMANTIC ENRICHMENT (KI Analyse)")
    print("-" * 80)

    try:
        # Wir versuchen den echten Provider
        try:
            provider = get_provider("cerebras")
            print("🤖 Provider: Cerebras Llama 3.3 70B (Async High-Performance)")
        except ValueError:
            print("⚠️  Provider: MOCK (Kein API Key gefunden in .env)")
            provider = get_provider("mock")

        enricher = GraphEnricher(graph_manager, provider)
        
        print("⏳ Starte Analyse aller Funktionen & Klassen...")
        t1 = time.time()
        
        # Batch Size 20 für maximale Geschwindigkeit bei Cerebras
        await enricher.enrich_nodes(batch_size=20)
        
        duration_enrich = time.time() - t1
        print(f"✅ Analyse abgeschlossen in {duration_enrich:.3f}s")
        
    except Exception as e:
        print(f"💥 Kritischer Fehler im Enricher: {e}")
        return

    # ---------------------------------------------------------
    # SCHRITT 3: FULL REPORT (Mit Dependencies!)
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("3️⃣  PHASE 3: VOLLSTÄNDIGER REPORT (Knoten + Verbindungen)")
    print("=" * 80)

    # Wir sortieren die Knoten alphabetisch
    all_nodes = sorted(graph.nodes(data=True))
    
    count = 0
    for node_id, attrs in all_nodes:
        # Wir filtern: Nur Code-Elemente (Funktionen/Klassen) ODER Dateien
        if "summary" in attrs or attrs.get("type") == "file":
            count += 1
            node_type = attrs.get("type", "unknown").upper()
            
            print(f"\n🔹 [{node_type}] {node_id}")
            print("-" * 60)
            
            # A) Summary anzeigen (falls vorhanden)
            if "summary" in attrs:
                print(f"📝 SUMMARY:\n   {attrs['summary']}")
                
                # Risiken
                risks = attrs.get("risks", [])
                if risks:
                    print("⚠️  RISIKEN:")
                    for i, risk in enumerate(risks, 1):
                        print(f"   {i}. {risk}")
            
            # B) BEZIEHUNGEN (Das neue Feature!)
            # 1. Outgoing: Wen brauche ich? (Dependencies / Imports)
            # Wir suchen Kanten, die von HIER weggehen
            dependencies = []
            for _, target, edge_data in graph.out_edges(node_id, data=True):
                edge_type = edge_data.get("type", "UNK")
                dependencies.append(f"{edge_type} -> {target}")
            
            if dependencies:
                print("🔗 ABHÄNGIGKEITEN (Ich brauche):")
                for dep in dependencies:
                    print(f"   - {dep}")

            # 2. Incoming: Wer braucht mich? (Usages / Impact)
            # Wir suchen Kanten, die HIERHER führen
            usages = []
            for source, _, edge_data in graph.in_edges(node_id, data=True):
                edge_type = edge_data.get("type", "UNK")
                usages.append(f"{source} ({edge_type})")
            
            if usages:
                print("👈 VERWENDUNG (Wer braucht mich?):")
                for usage in usages:
                    print(f"   - {usage}")

    print("\n" + "=" * 80)
    print("🏁 ANALYSE BEENDET")
    print(f"   Analysierte Elemente: {count}")
    print(f"   Gesamtdauer:          {time.time() - t0:.3f}s")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())