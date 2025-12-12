"""LLM Provider Protocol für einheitliche KI-Anbindung.

Definiert das Interface für alle LLM-Provider-Implementierungen.
Ermöglicht Dependency Injection und einfaches Testen mit Mocks.
"""

import os
from typing import Protocol

from openai import OpenAI


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
    """Cerebras-API-Integration für LLM-Inferenz.

    Diese Implementierung bindet die Cerebras-API über das OpenAI-kompatible
    Interface an. Sie verwendet den llama3.1-70b-Modell für schnelle und
    qualitativ hochwertige Inferenz.

    Die Klasse liest den API-Schlüssel aus der Umgebungsvariable
    CEREBRAS_API_KEY und initialisiert einen OpenAI-Client mit der
    Cerebras-API-Base-URL.

    Attributes:
        client: OpenAI-Client konfiguriert für Cerebras-API.
        model: Name des verwendeten Modells (llama3.1-70b).

    Raises:
        ValueError: Wenn CEREBRAS_API_KEY nicht gesetzt ist.
    """

    def __init__(self) -> None:
        """Initialisiert den CerebrasProvider mit API-Key aus Umgebungsvariable.

        Liest CEREBRAS_API_KEY aus os.environ und erstellt einen OpenAI-Client
        mit der Cerebras-API-Base-URL. Setzt das Standard-Modell auf llama3.1-70b.

        Raises:
            ValueError: Wenn CEREBRAS_API_KEY nicht gesetzt oder leer ist.
        """
        api_key = os.environ.get("CEREBRAS_API_KEY")
        if not api_key:
            raise ValueError("CEREBRAS_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key, base_url="https://api.cerebras.ai/v1")
        self.model = "llama3.1-70b"

    def send(self, system: str, user: str) -> str:  # pragma: no cover
        """Sendet Prompts an Cerebras-API und erhält Antwort.

        Erstellt einen Chat-Completion-Request mit System- und User-Prompts
        und gibt die generierte Antwort zurück. Verwendet temperature=0.2
        für präzise, deterministische Antworten.

        Args:
            system: System-Prompt für Kontext und Verhaltenssteuerung.
            user: User-Prompt mit konkreter Anfrage.

        Returns:
            String-Antwort vom LLM.

        Raises:
            ValueError: Wenn die Cerebras-API eine unerwartete oder leere
                Antwort zurückgibt. Dies tritt auf bei:
                - Leerer choices-Liste in der API-Antwort
                - None-Wert im message.content-Feld
            openai.APIError: Bei Netzwerk- oder API-Fehlern (von OpenAI-Client).

        Note:
            Call-Sites sollten ValueError abfangen und geeignete Fallback-
            oder Logging-Logik implementieren.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        if not response.choices:
            raise ValueError("Empty response from Cerebras API")
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Null content in Cerebras API response")
        return content


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
            >>> # Benötigt CEREBRAS_API_KEY Umgebungsvariable

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
