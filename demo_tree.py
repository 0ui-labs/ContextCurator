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
except ImportError as e:
    print("Fehler: Konnte 'codemap' nicht importieren.")
    print(f"Details: {e}")
    sys.exit(1)

def main():
    # 1. Start
    root_path = Path.cwd()
    print(f"🚀 Starte TreeGenerator im Ordner: {root_path.name}")
    print("-" * 50)

    # 2. Initialisierung
    generator = TreeGenerator()
    
    start_time = time.time()
    
    # 3. Die Magie (Scan)
    try:
        report = generator.generate(root_path)
    except Exception as e:
        print(f"💥 Kritischer Fehler beim Scannen: {e}")
        sys.exit(1)

    duration = time.time() - start_time

    # 4. Ergebnis-Ausgabe (Der "Report")
    print(report.tree_string)
    print("-" * 50)
    print("📊 STATISTIK:")
    print(f"   Dateien gefunden:  {report.total_files}")
    print(f"   Ordner gescannt:   {report.total_folders}")
    print(f"   Geschätzte Token:  ~{report.estimated_tokens}")
    print(f"   Dauer:             {duration:.4f} Sekunden")
    print("-" * 50)
    
    # Kleiner Check ob .gitignore funktioniert hat
    if ".git" not in report.tree_string and ".venv" not in report.tree_string:
        print("✅ Ignore-Check: .git und .venv wurden korrekt ignoriert.")
    else:
        print("❌ Ignore-Check: WARNUNG! Versteckte Ordner wurden gefunden.")

if __name__ == "__main__":
    main()