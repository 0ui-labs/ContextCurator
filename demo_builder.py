import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Pfad-Setup für Imports
sys.path.append(str(Path.cwd() / "src"))

try:
    from codemap.engine import MapBuilder
except ImportError as e:
    print(f"❌ Import Fehler: {e}")
    sys.exit(1)


def get_root_path(cli_arg: str | None) -> Path:
    """Bestimme das Root-Verzeichnis für den Scan.

    Priorität:
    1. CLI-Argument (falls angegeben)
    2. ./src (falls vorhanden)
    3. Aktuelles Verzeichnis
    """
    if cli_arg:
        path = Path(cli_arg)
        if not path.exists():
            print(f"❌ Verzeichnis existiert nicht: {path}")
            sys.exit(1)
        return path.resolve()

    src_path = Path.cwd() / "src"
    if src_path.exists() and src_path.is_dir():
        return src_path

    return Path.cwd()


def main():
    parser = argparse.ArgumentParser(
        description="Demo für MapBuilder - baut einen Code-Graph aus Quelldateien"
    )
    parser.add_argument(
        "root",
        nargs="?",
        help="Root-Verzeichnis zum Scannen (Standard: ./src falls vorhanden, sonst .)",
    )
    args = parser.parse_args()

    # ---------------------------------------------------------
    # 🚀 SCHRITT 1: Initialisierung
    # ---------------------------------------------------------
    root_path = get_root_path(args.root)
    print(f"🚀 Starte MapBuilder für: {root_path}")
    print("=" * 60)

    builder = MapBuilder()

    # ---------------------------------------------------------
    # 📂 SCHRITT 2: Graph bauen
    # ---------------------------------------------------------
    print("\n📂 Baue Code-Graph...")
    start_time = time.time()

    try:
        manager = builder.build(root_path)
    except Exception as e:
        print(f"💥 Fehler beim Graph-Bau: {e}")
        sys.exit(1)

    build_duration = time.time() - start_time
    print(f"✅ Graph gebaut in {build_duration:.4f} Sekunden")

    # ---------------------------------------------------------
    # 📊 SCHRITT 3: Statistiken anzeigen
    # ---------------------------------------------------------
    print("\n📊 Graph-Statistiken:")
    print("-" * 40)

    stats = manager.graph_stats
    print(f"   Knoten:  {stats.get('nodes', 0)}")
    print(f"   Kanten:  {stats.get('edges', 0)}")

    # Zähle verschiedene Knotentypen
    graph = manager.graph
    file_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") == "file"]
    code_nodes = [n for n, d in graph.nodes(data=True) if d.get("type") in ("function", "class", "method")]

    print(f"   Dateien: {len(file_nodes)}")
    print(f"   Code-Elemente: {len(code_nodes)}")

    # Zähle Kantentypen
    contains_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("relationship") == "CONTAINS"]
    imports_edges = [(u, v) for u, v, d in graph.edges(data=True) if d.get("relationship") == "IMPORTS"]

    print(f"   CONTAINS-Kanten: {len(contains_edges)}")
    print(f"   IMPORTS-Kanten:  {len(imports_edges)}")

    # ---------------------------------------------------------
    # 💾 SCHRITT 4: Graph speichern (optional)
    # ---------------------------------------------------------
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "graph.json"

    print(f"\n💾 Speichere Graph nach: {output_path}")
    save_start = time.time()

    try:
        manager.save(output_path)
        save_duration = time.time() - save_start
        print(f"✅ Gespeichert in {save_duration:.4f} Sekunden")
    except Exception as e:
        print(f"⚠️  Speichern fehlgeschlagen: {e}")

    # ---------------------------------------------------------
    # 📋 SCHRITT 5: Beispieldaten anzeigen
    # ---------------------------------------------------------
    print("\n📋 Beispiel-Knoten (Top 10 Dateien):")
    print("-" * 40)

    if not file_nodes:
        print("   (keine Datei-Knoten gefunden)")
    else:
        for i, node_id in enumerate(file_nodes[:10]):
            node_data = graph.nodes.get(node_id, {})
            size = node_data.get("size", 0)
            tokens = node_data.get("token_est", 0)
            print(f"   {i+1}. {node_id} ({size} bytes, ~{tokens} tokens)")

        if len(file_nodes) > 10:
            print(f"   ... und {len(file_nodes) - 10} weitere Dateien")

    print("\n📋 Beispiel-Kanten (Top 5 CONTAINS):")
    print("-" * 40)

    if not contains_edges:
        print("   (keine CONTAINS-Kanten gefunden)")
    else:
        for i, (source, target) in enumerate(contains_edges[:5]):
            source_data = graph.nodes.get(source, {})
            target_data = graph.nodes.get(target, {})
            source_path = source_data.get("path", source)
            target_name = target_data.get("name", target)
            target_type = target_data.get("type", "?")
            print(f"   {source_path} → {target_name} ({target_type})")

        if len(contains_edges) > 5:
            print(f"   ... und {len(contains_edges) - 5} weitere CONTAINS-Kanten")

    # ---------------------------------------------------------
    # 📊 ZUSAMMENFASSUNG
    # ---------------------------------------------------------
    total_duration = time.time() - start_time

    print("\n" + "=" * 60)
    print("📊 ZUSAMMENFASSUNG")
    print("=" * 60)
    print(f"   Verarbeitete Dateien:  {len(file_nodes)}")
    print(f"   Gefundene Code-Elemente: {len(code_nodes)}")
    print(f"   Graph-Knoten:          {stats.get('nodes', 0)}")
    print(f"   Graph-Kanten:          {stats.get('edges', 0)}")
    print(f"   Build-Dauer:           {build_duration:.4f} Sekunden")
    print(f"   Gesamt-Dauer:          {total_duration:.4f} Sekunden")
    print("=" * 60)
    print("✅ Demo abgeschlossen!")


if __name__ == "__main__":
    main()
