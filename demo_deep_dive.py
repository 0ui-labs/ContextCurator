import asyncio
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Environment Variablen laden
load_dotenv()

# Pfad-Setup
sys.path.append(str(Path.cwd() / "src"))

try:
    from codemap.scout import TreeGenerator, FileWalker, StructureAdvisor
    from codemap.mapper import ParserEngine, ContentReader
    from codemap.graph import GraphManager
    from codemap.engine import GraphEnricher
    from codemap.core.llm import get_provider
except ImportError as e:
    print(f"❌ Import Fehler: {e}")
    sys.exit(1)

async def main():
    root_path = Path.cwd() / "src"
    
    print("=" * 80)
    print(f"🚀 ContextCurator: ULTIMATE DEEP DIVE (Fixed)")
    print(f"📂 Ziel: {root_path}")
    print("=" * 80)

    # ---------------------------------------------------------
    # SCHRITT 0: Der Rohe Blick (TreeGenerator)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("0️⃣  PHASE 0: VISUALISIERUNG (TreeGenerator)")
    print("-" * 80)
    
    t0 = time.time()
    tree_gen = TreeGenerator()
    tree_report = tree_gen.generate(root_path)
    
    print(tree_report.tree_string)
    print(f"\n✅ Tree generiert in {time.time() - t0:.4f}s")
    print(f"📊 Statistik: {tree_report.total_files} Dateien, {tree_report.total_folders} Ordner")

    # ---------------------------------------------------------
    # SCHRITT 1: Die Entscheidung (StructureAdvisor)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("1️⃣  PHASE 1: FILTER-STRATEGIE (StructureAdvisor + AI)")
    print("-" * 80)
    
    try:
        try:
            provider = get_provider("cerebras")
            print("🤖 KI: Cerebras Llama 3.3 70B")
        except ValueError:
            print("⚠️ KI: Mock (Kein Key)")
            provider = get_provider("mock")
            
        advisor = StructureAdvisor(provider)
        ignore_patterns = await advisor.analyze(tree_report)
        
        print("🚫 KI-Empfohlene Ignore-Patterns:")
        if not ignore_patterns:
            print("   (Keine Patterns vorgeschlagen - alles scheint wichtig zu sein)")
        for p in ignore_patterns:
            print(f"   ❌ {p}")
            
    except Exception as e:
        print(f"💥 Fehler im Advisor: {e}")
        return

    # ---------------------------------------------------------
    # SCHRITT 2: Die Inventur (FileWalker)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("2️⃣  PHASE 2: INVENTUR (FileWalker)")
    print("-" * 80)
    
    walker = FileWalker()
    inventory = walker.walk(root_path, ignore_patterns=ignore_patterns)
    inventory.sort(key=lambda x: str(x.path))
    
    print(f"📄 Relevante Dateien ({len(inventory)}):")
    for entry in inventory:
        print(f"   ✅ {entry.path} ({entry.size} bytes)")

    # ---------------------------------------------------------
    # SCHRITT 3: Struktur-Aufbau (Mapper -> Graph)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("3️⃣  PHASE 3: STRUKTUR-SCAN (Parser & Graph)")
    print("-" * 80)
    
    t_graph = time.time()
    graph_manager = GraphManager()
    parser = ParserEngine()
    reader = ContentReader()
    
    print("⚙️  Parse Dateien & Baue Graph...")
    for entry in inventory:
        # 1. Datei zum Graph
        graph_manager.add_file(entry)
        
        # 2. Inhalt lesen
        full_path = root_path / entry.path
        try:
            content = reader.read_file(full_path)
            
            # 3. Parsen
            lang = parser.get_language_id(full_path)
            if lang:
                # FIX 1: Methode heißt .parse(), nicht .extract_definitions()
                nodes = parser.parse(content, lang)
                
                # FIX 2: Loop über Nodes, da add_node nur einzelne Items nimmt
                for node in nodes:
                    graph_manager.add_node(str(entry.path), node)
                
                # Dependencies (Vereinfacht für Demo)
                for node in nodes:
                    if node.type == "import":
                        graph_manager.add_dependency(str(entry.path), node.name)
                        
        except Exception as e:
            print(f"   ⚠️ Fehler bei {entry.path}: {e}")

    print(f"✅ Graph fertig in {time.time() - t_graph:.3f}s")
    print(f"📊 Nodes: {graph_manager.graph_stats['nodes']}, Edges: {graph_manager.graph_stats['edges']}")

    # ---------------------------------------------------------
    # SCHRITT 4: Das Verständnis (Enricher)
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("4️⃣  PHASE 4: SEMANTIC ENRICHMENT (KI Analyse)")
    print("-" * 80)
    
    enricher = GraphEnricher(graph_manager, provider)
    
    print("⏳ Sende Code an KI (Parallel Batches)...")
    t_enrich = time.time()
    await enricher.enrich_nodes(batch_size=50)
    print(f"✅ Enrichment fertig in {time.time() - t_enrich:.3f}s")

    # ---------------------------------------------------------
    # SCHRITT 5: FULL REPORT
    # ---------------------------------------------------------
    print("\n" + "="*80)
    print("5️⃣  PHASE 5: VOLLSTÄNDIGER REPORT")
    print("=" * 80)

    all_nodes = sorted(graph_manager.graph.nodes(data=True))
    
    count = 0
    for node_id, attrs in all_nodes:
        node_type = attrs.get("type", "unknown")
        
        # Zeige alles an, was Code (Funktion/Klasse) oder Datei ist
        # Filterung: Wir wollen sehen ob KI-Daten da sind
        
        print(f"\n🔹 [{node_type.upper()}] {node_id}")
        print("-" * 60)
        
        # 1. KI Wissen (Summary/Risks)
        if "summary" in attrs:
            print(f"🧠 AI SUMMARY:\n   {attrs['summary']}")
            
            risks = attrs.get("risks", [])
            if risks:
                print("\n⚠️  AI RISKS:")
                for r in risks:
                    print(f"   - {r}")
        else:
            if node_type in ["function", "class"]:
                print("   (❌ FEHLT: Keine KI-Daten - Batch Fehler?)")
            else:
                print("   (Datei/Import - Kein Enrichment vorgesehen)")

        # 2. Verbindungen (Edges)
        # Outgoing (Ich brauche...)
        out_edges = graph_manager.graph.out_edges(node_id, data=True)
        deps = []
        for _, target, d in out_edges:
            edge_t = d.get('type', 'UNK')
            deps.append(f"{edge_t} -> {target}")
            
        if deps:
            print("\n🔗 DEPENDENCIES (Outgoing):")
            for d in deps:
                print(f"   - {d}")
                
        # Incoming (Werde gebraucht von...)
        in_edges = graph_manager.graph.in_edges(node_id, data=True)
        usages = []
        for source, _, d in in_edges:
            edge_t = d.get('type', 'UNK')
            usages.append(f"{source} ({edge_t})")
            
        if usages:
            print("\n👈 USAGE (Incoming):")
            for u in usages:
                print(f"   - {u}")

        count += 1

    print("\n" + "="*80)
    print(f"🏁 DONE. {count} Elemente angezeigt.")

if __name__ == "__main__":
    asyncio.run(main())