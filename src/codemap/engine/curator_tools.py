"""CuratorTools for LLM agent code navigation.

This module provides the CuratorTools class that wraps MapRenderer methods
as tools for the LLM agent. Each tool represents a zoom level for
navigating the code graph with LLM-friendly interfaces and error messages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from codemap.engine.map_renderer import MapRenderer


class CuratorTools:
    """Tools für den Curator Agent zum Navigieren im Code-Verzeichnis.

    Stellt 5 Zoom-Level-Tools bereit, die MapRenderer-Methoden wrappen
    und LLM-freundliche Schnittstellen bieten.
    """

    def __init__(self, map_renderer: MapRenderer) -> None:
        """Initialisiere CuratorTools mit MapRenderer.

        Args:
            map_renderer: MapRenderer-Instanz für Graph-Rendering.
        """
        self._renderer = map_renderer

    def get_project_overview(self) -> str:
        """Zeigt die Projektübersicht (Level 0).

        Nutze dies als Einstiegspunkt um zu verstehen, wie das Projekt
        strukturiert ist. Zeigt Hauptbereiche (Packages) und
        Architektur-Hinweise (inter-package Imports).

        Returns:
            Markdown-String mit Projektübersicht.
        """
        return self._renderer.render_overview()

    def zoom_to_package(self, package_path: str) -> str:
        """Zoomt in ein Package hinein (Level 1).

        Zeigt alle Module im Package, interne Struktur (Imports zwischen
        Modulen), externe Schnittstellen (Imports über Package-Grenzen)
        und Risiken. Nutze dies um Package-Abhängigkeiten zu verstehen.

        Args:
            package_path: Pfad zum Package, z.B. 'src/auth' oder
                'src/engine'.

        Returns:
            Markdown-String mit Package-Details.

        Raises:
            ValueError: Wenn Package nicht gefunden oder kein Package-Node.
        """
        try:
            return self._renderer.render_package(package_path)
        except ValueError:
            raise ValueError(
                f"Package '{package_path}' nicht gefunden"
                " oder kein Package-Node"
            ) from None

    def zoom_to_module(self, file_path: str) -> str:
        """Zoomt in ein Modul hinein (Level 2).

        Zeigt alle Funktionen/Klassen im Modul, Abhängigkeiten
        (importiert/wird importiert von) und Risiken. Nutze dies um zu
        sehen wer ein Modul importiert.

        Args:
            file_path: Pfad zur Datei, z.B. 'src/auth/session.py'.

        Returns:
            Markdown-String mit Modul-Details.

        Raises:
            ValueError: Wenn Modul nicht gefunden oder kein File-Node.
        """
        try:
            return self._renderer.render_module(file_path)
        except ValueError:
            raise ValueError(
                f"Modul '{file_path}' nicht gefunden"
                " oder kein File-Node"
            ) from None

    def zoom_to_symbol(self, file_path: str, symbol_name: str) -> str:
        """Zoomt in eine Funktion oder Klasse hinein (Level 3).

        Zeigt Signatur, Verhalten (Summary), Aufrufer (wer importiert das
        Parent-Modul) und Risiken. Nutze dies um den Impact einer
        Symbol-Änderung zu verstehen.

        Args:
            file_path: Pfad zur Datei, z.B. 'src/auth/session.py'.
            symbol_name: Name des Symbols, z.B. 'SessionManager' oder
                'validate_token'.

        Returns:
            Markdown-String mit Symbol-Details.

        Raises:
            ValueError: Wenn Symbol nicht gefunden.
        """
        try:
            return self._renderer.render_symbol(file_path, symbol_name)
        except ValueError:
            raise ValueError(
                f"Symbol '{file_path}::{symbol_name}' nicht gefunden"
            ) from None

    def show_code(self, file_path: str, symbol_name: str) -> str:
        """Zeigt den tatsächlichen Quellcode (Level 4).

        Zeigt Code mit Zeilennummern. Nutze dies nur wenn du den genauen
        Code sehen musst - für Kontext-Verständnis reichen Level 2-3.

        Args:
            file_path: Pfad zur Datei, z.B. 'src/auth/session.py'.
            symbol_name: Name des Symbols, z.B. 'validate_token'.

        Returns:
            Markdown-String mit Quellcode und Zeilennummern.

        Raises:
            ValueError: Wenn root_path nicht gesetzt, Datei nicht gefunden,
                Symbol nicht gefunden oder ungültiger Zeilenbereich.
        """
        return self._renderer.render_code(file_path, symbol_name)
