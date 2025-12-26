"""
Suggestion Engine - Inteligentny silnik sugestii kontekstowych

Generuje sugestie na podstawie:
- Aktualnego kontekstu projektu
- Historii komend
- Częściowego wejścia
- Wzorców użycia
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from collections import Counter
from datetime import datetime, timedelta
import re


@dataclass
class Suggestion:
    """Pojedyncza sugestia"""

    text: str
    command: str
    category: str
    score: float = 0.0
    description: Optional[str] = None
    shortcut: Optional[str] = None


@dataclass
class UsagePattern:
    """Wzorzec użycia komend"""

    sequence: Tuple[str, ...]
    count: int = 1
    last_used: datetime = field(default_factory=datetime.now)


class SuggestionEngine:
    """
    Silnik sugestii dla nawigacji głosowej

    Funkcje:
    - Sugestie kontekstowe na podstawie stanu projektu
    - Uczenie się wzorców użycia
    - Autouzupełnianie
    - Ranking sugestii
    """

    # Typowe sekwencje komend
    COMMON_SEQUENCES = [
        ("pull", "build", "test"),
        ("build", "test", "push"),
        ("clean", "build"),
        ("checkout", "pull", "build"),
        ("commit", "push"),
        ("build", "run"),
        ("compose up", "compose logs"),
    ]

    # Sugestie dla różnych kontekstów
    CONTEXT_SUGGESTIONS = {
        "makefile": [
            Suggestion("zbuduj projekt", "make all", "make", 0.9, "Wykonaj domyślny cel"),
            Suggestion("wyczyść", "make clean", "make", 0.7, "Wyczyść build"),
            Suggestion("uruchom testy", "make test", "make", 0.8, "Uruchom testy"),
            Suggestion("zainstaluj", "make install", "make", 0.6),
        ],
        "git": [
            Suggestion("sprawdź status", "git status", "git", 0.95),
            Suggestion("pobierz zmiany", "git pull", "git", 0.85),
            Suggestion("wypchnij zmiany", "git push", "git", 0.8),
            Suggestion("zatwierdź zmiany", "git commit", "git", 0.75),
            Suggestion("pokaż historię", "git log --oneline -10", "git", 0.6),
        ],
        "docker": [
            Suggestion("zbuduj obraz", "docker build -t app .", "docker", 0.85),
            Suggestion("uruchom kontener", "docker run", "docker", 0.8),
            Suggestion("pokaż kontenery", "docker ps", "docker", 0.9),
            Suggestion("pokaż obrazy", "docker images", "docker", 0.7),
        ],
        "docker_compose": [
            Suggestion("uruchom serwisy", "docker compose up -d", "docker", 0.9),
            Suggestion("zatrzymaj serwisy", "docker compose down", "docker", 0.85),
            Suggestion("pokaż logi", "docker compose logs -f", "docker", 0.8),
            Suggestion("restart", "docker compose restart", "docker", 0.7),
        ],
        "python": [
            Suggestion("uruchom testy", "pytest", "python", 0.9),
            Suggestion("zainstaluj zależności", "pip install -r requirements.txt", "python", 0.85),
            Suggestion("sprawdź typy", "mypy .", "python", 0.6),
            Suggestion("formatuj kod", "black .", "python", 0.65),
        ],
    }

    # Sugestie po błędach
    ERROR_SUGGESTIONS = {
        "permission denied": [
            Suggestion("uruchom z sudo", "sudo !!", "shell", 0.8),
            Suggestion("zmień uprawnienia", "chmod +x", "shell", 0.7),
        ],
        "command not found": [
            Suggestion("zainstaluj przez apt", "apt install", "shell", 0.6),
            Suggestion("zainstaluj przez pip", "pip install", "python", 0.6),
        ],
        "merge conflict": [
            Suggestion("pokaż konflikty", "git diff --name-only --diff-filter=U", "git", 0.9),
            Suggestion("przerwij merge", "git merge --abort", "git", 0.7),
        ],
    }

    def __init__(self):
        self.usage_patterns: Dict[Tuple[str, ...], UsagePattern] = {}
        self.command_frequency: Counter = Counter()
        self.last_commands: List[str] = []

    def get_suggestions(
        self,
        partial_input: str = "",
        context: Optional[Dict] = None,
        last_result: Optional[Dict] = None,
        max_suggestions: int = 5,
    ) -> List[Suggestion]:
        """
        Generuje listę sugestii

        Args:
            partial_input: Częściowy tekst wpisany przez użytkownika
            context: Kontekst projektu z ContextManager
            last_result: Wynik ostatniego polecenia
            max_suggestions: Maksymalna liczba sugestii

        Returns:
            Lista sugestii posortowana wg score
        """
        candidates: List[Suggestion] = []

        # Sugestie na podstawie kontekstu projektu
        if context:
            candidates.extend(self._get_context_suggestions(context))

        # Sugestie po błędach
        if last_result and not last_result.get("success", True):
            candidates.extend(self._get_error_suggestions(last_result))

        # Sugestie na podstawie wzorców
        candidates.extend(self._get_pattern_suggestions())

        # Sugestie na podstawie częstotliwości
        candidates.extend(self._get_frequency_suggestions())

        # Filtruj po częściowym wejściu
        if partial_input:
            candidates = self._filter_by_input(candidates, partial_input)

        # Usuń duplikaty i sortuj
        seen: Set[str] = set()
        unique_candidates = []
        for c in candidates:
            if c.command not in seen:
                seen.add(c.command)
                unique_candidates.append(c)

        unique_candidates.sort(key=lambda s: s.score, reverse=True)

        return unique_candidates[:max_suggestions]

    def _get_context_suggestions(self, context: Dict) -> List[Suggestion]:
        """Sugestie na podstawie kontekstu projektu"""
        suggestions = []
        project = context.get("project", {})

        if project.get("has_makefile"):
            suggestions.extend(self.CONTEXT_SUGGESTIONS["makefile"])

        if project.get("has_git"):
            suggestions.extend(self.CONTEXT_SUGGESTIONS["git"])

        if project.get("has_docker"):
            if context.get("has_docker_compose"):
                suggestions.extend(self.CONTEXT_SUGGESTIONS["docker_compose"])
            else:
                suggestions.extend(self.CONTEXT_SUGGESTIONS["docker"])

        if project.get("has_python"):
            suggestions.extend(self.CONTEXT_SUGGESTIONS["python"])

        return suggestions

    def _get_error_suggestions(self, last_result: Dict) -> List[Suggestion]:
        """Sugestie po wystąpieniu błędu"""
        suggestions = []
        error = last_result.get("error", "").lower()

        for error_pattern, error_suggestions in self.ERROR_SUGGESTIONS.items():
            if error_pattern in error:
                for s in error_suggestions:
                    # Zwiększ score dla sugestii po błędach
                    boosted = Suggestion(
                        text=s.text,
                        command=s.command,
                        category=s.category,
                        score=s.score + 0.2,
                        description=s.description,
                        shortcut=s.shortcut,
                    )
                    suggestions.append(boosted)

        return suggestions

    def _get_pattern_suggestions(self) -> List[Suggestion]:
        """Sugestie na podstawie wzorców użycia"""
        suggestions = []

        if len(self.last_commands) < 1:
            return suggestions

        last_cmd = self.last_commands[-1]

        # Znajdź wzorce zaczynające się od ostatniej komendy
        for sequence, pattern in self.usage_patterns.items():
            if len(sequence) > 1 and sequence[0] == last_cmd:
                next_cmd = sequence[1]
                # Score bazuje na częstotliwości wzorca
                score = min(0.9, 0.5 + pattern.count * 0.1)
                suggestions.append(
                    Suggestion(
                        text=f"następnie: {next_cmd}",
                        command=next_cmd,
                        category="wzorzec",
                        score=score,
                        description=f"Używane {pattern.count}x",
                    )
                )

        return suggestions

    def _get_frequency_suggestions(self) -> List[Suggestion]:
        """Sugestie na podstawie częstotliwości użycia"""
        suggestions = []

        for cmd, count in self.command_frequency.most_common(3):
            score = min(0.7, 0.3 + count * 0.05)
            suggestions.append(
                Suggestion(
                    text=f"często używane: {cmd}",
                    command=cmd,
                    category="historia",
                    score=score,
                    description=f"Użyte {count}x",
                )
            )

        return suggestions

    def _filter_by_input(self, candidates: List[Suggestion], partial: str) -> List[Suggestion]:
        """Filtruje sugestie po częściowym wejściu"""
        partial_lower = partial.lower()
        filtered = []

        for s in candidates:
            # Sprawdź czy pasuje do tekstu lub komendy
            if partial_lower in s.text.lower() or partial_lower in s.command.lower():
                # Zwiększ score dla dokładniejszych dopasowań
                if s.text.lower().startswith(partial_lower):
                    s.score += 0.1
                filtered.append(s)

        return filtered

    def record_command(self, command: str):
        """Zapisuje wykonaną komendę do historii"""
        # Aktualizuj częstotliwość
        self.command_frequency[command] += 1

        # Aktualizuj wzorce
        if self.last_commands:
            for i in range(len(self.last_commands)):
                sequence = tuple(self.last_commands[i:] + [command])
                if len(sequence) <= 3:  # Max 3-elementowe sekwencje
                    if sequence in self.usage_patterns:
                        self.usage_patterns[sequence].count += 1
                        self.usage_patterns[sequence].last_used = datetime.now()
                    else:
                        self.usage_patterns[sequence] = UsagePattern(sequence)

        # Aktualizuj ostatnie komendy
        self.last_commands.append(command)
        if len(self.last_commands) > 10:
            self.last_commands = self.last_commands[-10:]

    def get_completion(self, partial: str) -> Optional[str]:
        """
        Zwraca autouzupełnienie dla częściowego wejścia

        Args:
            partial: Częściowy tekst

        Returns:
            Pełna komenda lub None
        """
        partial_lower = partial.lower()

        # Szukaj w najczęściej używanych
        for cmd, _ in self.command_frequency.most_common(20):
            if cmd.lower().startswith(partial_lower):
                return cmd

        # Szukaj w standardowych sugestiach
        for category_suggestions in self.CONTEXT_SUGGESTIONS.values():
            for s in category_suggestions:
                if s.text.lower().startswith(partial_lower):
                    return s.text
                if s.command.lower().startswith(partial_lower):
                    return s.command

        return None

    def get_next_likely_command(self) -> Optional[str]:
        """Przewiduje najbardziej prawdopodobną następną komendę"""
        if not self.last_commands:
            return None

        last_cmd = self.last_commands[-1]
        best_match: Optional[Tuple[str, int]] = None

        for sequence, pattern in self.usage_patterns.items():
            if sequence[0] == last_cmd and len(sequence) > 1:
                if best_match is None or pattern.count > best_match[1]:
                    best_match = (sequence[1], pattern.count)

        return best_match[0] if best_match else None

    def format_suggestions_for_voice(self, suggestions: List[Suggestion]) -> str:
        """Formatuje sugestie do odczytu głosowego"""
        if not suggestions:
            return "Brak sugestii."

        lines = ["Dostępne opcje:"]
        for i, s in enumerate(suggestions[:5], 1):
            lines.append(f"{i}. {s.text}")

        return " ".join(lines)

    def format_suggestions_for_display(self, suggestions: List[Suggestion]) -> str:
        """Formatuje sugestie do wyświetlenia"""
        if not suggestions:
            return "Brak sugestii."

        lines = ["┌─ Sugestie ─────────────────────────┐"]
        for i, s in enumerate(suggestions[:5], 1):
            shortcut = f"[{s.shortcut}]" if s.shortcut else f"[{i}]"
            desc = f" - {s.description}" if s.description else ""
            lines.append(f"│ {shortcut:5} {s.text:25}{desc}")
        lines.append("└────────────────────────────────────┘")

        return "\n".join(lines)
