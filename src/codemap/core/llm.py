"""LLM Provider Protocol für einheitliche KI-Anbindung.

Definiert das Interface für alle LLM-Provider-Implementierungen.
Ermöglicht Dependency Injection und einfaches Testen mit Mocks.
"""

from typing import Protocol


class LLMProvider(Protocol):
    """LLM Provider Protocol für einheitliche KI-Anbindung.

    Definiert das Interface für alle LLM-Provider-Implementierungen.
    Ermöglicht Dependency Injection und einfaches Testen mit Mocks.

    Methods:
        send: Sendet System- und User-Prompts an LLM, gibt Antwort zurück.
    """

    def send(self, system: str, user: str) -> str:
        """Sendet Prompts an LLM und erhält Antwort.

        Args:
            system: System-Prompt für Kontext und Verhaltenssteuerung.
            user: User-Prompt mit konkreter Anfrage.

        Returns:
            String-Antwort vom LLM.
        """
        ...  # pragma: no cover


class MockProvider:
    """Mock-Implementierung des LLMProvider für deterministische Tests.

    Diese Test-Double-Implementierung ermöglicht deterministisches Testen
    ohne echte LLM-Aufrufe. Gibt einen fest vordefinierten String im
    gitignore-Format zurück, unabhängig von den Eingabeparametern.

    Verwendungszweck:
        - Unit-Tests für Komponenten, die LLMProvider benötigen
        - Vermeidung von echten API-Aufrufen in Tests
        - Schnelle, deterministische Testausführung

    Returns:
        Immer derselbe vordefinierte String mit typischen gitignore-Mustern.
    """

    def send(self, system: str, user: str) -> str:  # noqa: ARG002
        """Gibt einen deterministischen String im gitignore-Format zurück.

        Ignoriert die übergebenen Prompts und gibt immer denselben
        vordefinierten String zurück. Dieser simuliert typische
        gitignore-Patterns für spätere StructureAdvisor-Tests.

        Args:
            system: System-Prompt (wird ignoriert).
            user: User-Prompt (wird ignoriert).

        Returns:
            Fest vordefinierter String mit gitignore-Patterns:
            "node_modules/\ndist/\n.venv/"
        """
        return "node_modules/\ndist/\n.venv/"


class CerebrasProvider:
    """Stub-Implementierung für künftige Cerebras-API-Integration.

    Diese Platzhalter-Implementierung bereitet die Integration der
    Cerebras-API vor. Aktuell wirft die send-Methode NotImplementedError.
    Der Stub dient als strukturelle Vorbereitung für die spätere
    Anbindung der echten Cerebras-API mit API-Schlüssel-Authentifizierung.

    Verwendungszweck:
        - Strukturelle Vorbereitung für Cerebras-Integration
        - Signalisiert geplante künftige Implementierung
        - Ermöglicht frühzeitige Architektur-Planung

    Note:
        Diese Klasse ist noch nicht funktionsfähig und dient nur als Stub.
        Die echte API-Integration erfolgt in einer späteren Phase.
    """

    def send(self, system: str, user: str) -> str:
        """Wirft NotImplementedError - Stub für künftige Cerebras-API-Calls.

        Diese Methode ist noch nicht implementiert und wirft immer
        NotImplementedError. In der echten Implementierung wird hier
        die Kommunikation mit der Cerebras-API stattfinden.

        Args:
            system: System-Prompt für Kontext (noch nicht verwendet).
            user: User-Prompt mit Anfrage (noch nicht verwendet).

        Returns:
            String-Antwort vom LLM (in echter Implementierung).

        Raises:
            NotImplementedError: Immer, da dies nur ein Stub ist.
        """
        raise NotImplementedError("CerebrasProvider not yet implemented")


def get_provider(name: str = "mock") -> LLMProvider:
    """Factory-Funktion zur Erzeugung von LLM-Provider-Instanzen.

    Diese Funktion implementiert das Factory-Pattern für LLM-Provider und
    ermöglicht die einfache Instanziierung verschiedener Provider-Typen
    über einen einheitlichen String-basierten Namen. Sie abstrahiert die
    konkrete Implementierung und gibt Instanzen zurück, die dem
    LLMProvider-Protocol entsprechen.

    Das Factory-Pattern bietet mehrere Vorteile:
        - Zentrale Kontrolle über Provider-Erzeugung
        - Entkopplung von konkreten Implementierungsklassen
        - Einfacher Austausch von Providern zur Laufzeit
        - Type-Safety durch LLMProvider-Protocol als Return-Type

    Verfügbare Provider:
        - "mock": MockProvider für deterministische Tests ohne API-Aufrufe
        - "cerebras": CerebrasProvider für Cerebras-API (noch nicht vollständig)

    Standard-Verhalten:
        Ohne Parameter wird der MockProvider zurückgegeben. Dies ist ideal
        für Tests und Entwicklung, da keine echten API-Aufrufe erfolgen.

    Args:
        name: Name des gewünschten Providers. Standard ist "mock".

    Returns:
        Eine Instanz des angeforderten Providers, die dem LLMProvider-Protocol
        entspricht und die send()-Methode implementiert.

    Raises:
        ValueError: Wenn ein unbekannter Provider-Name übergeben wird.

    Examples:
        Standard-Verwendung mit MockProvider (ohne Parameter):
            >>> provider = get_provider()
            >>> result = provider.send("system prompt", "user prompt")
            >>> print(result)
            node_modules/
            dist/
            .venv/

        Explizite Auswahl des MockProviders:
            >>> provider = get_provider("mock")
            >>> result = provider.send("Analyze code", "What patterns?")

        Verwendung des CerebrasProviders:
            >>> provider = get_provider("cerebras")
            >>> # Hinweis: Wirft aktuell NotImplementedError, da Stub

        Fehlerbehandlung bei unbekanntem Provider:
            >>> try:
            ...     provider = get_provider("unknown")
            ... except ValueError as e:
            ...     print(f"Error: {e}")
            Error: Unknown provider: unknown
    """
    if name == "mock":
        return MockProvider()
    elif name == "cerebras":
        return CerebrasProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")
