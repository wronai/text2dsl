"""
DSL Parser - Parser języka domenowego dla text2dsl

Obsługuje składnię:
- Naturalne komendy: "uruchom testy", "zbuduj projekt"
- Skróty kontekstowe: "dalej", "powtórz", "cofnij"
- Komendy złożone: "zbuduj i uruchom testy"
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum, auto
import re


class CommandType(Enum):
    """Typy komend rozpoznawane przez parser"""
    MAKE = auto()
    SHELL = auto()
    GIT = auto()
    DOCKER = auto()
    PYTHON = auto()
    CONTEXT = auto()  # komendy kontekstowe: dalej, cofnij, powtórz
    QUERY = auto()    # pytania: co mogę zrobić?, jaki status?
    COMPOUND = auto() # komendy złożone


@dataclass
class ParsedCommand:
    """Sparsowana komenda DSL"""
    type: CommandType
    action: str
    target: Optional[str] = None
    args: List[str] = field(default_factory=list)
    flags: Dict[str, Any] = field(default_factory=dict)
    raw_input: str = ""
    confidence: float = 1.0
    alternatives: List['ParsedCommand'] = field(default_factory=list)
    detected_language: str = "pl"


# Wielojęzyczne mapowania słów kluczowych
MULTILANG_KEYWORDS = {
    CommandType.MAKE: {
        "pl": ["make", "zbuduj", "kompiluj", "cel", "uruchom cel"],
        "de": ["make", "bauen", "kompilieren", "ziel", "ausführen"],
        "en": ["make", "build", "compile", "target", "run target"],
    },
    CommandType.SHELL: {
        "pl": ["shell", "bash", "terminal", "uruchom", "wykonaj", "polecenie"],
        "de": ["shell", "bash", "terminal", "ausführen", "befehl"],
        "en": ["shell", "bash", "terminal", "run", "execute", "command"],
    },
    CommandType.GIT: {
        "pl": ["git", "commit", "push", "pull", "gałąź", "zatwierdź", "wypchnij", "pobierz"],
        "de": ["git", "commit", "push", "pull", "zweig", "bestätigen", "hochladen", "herunterladen"],
        "en": ["git", "commit", "push", "pull", "branch", "confirm", "upload", "download"],
    },
    CommandType.DOCKER: {
        "pl": ["docker", "kontener", "obraz", "compose", "uruchom kontener", "zbuduj obraz"],
        "de": ["docker", "container", "image", "compose", "container starten", "image bauen"],
        "en": ["docker", "container", "image", "compose", "run container", "build image"],
    },
    CommandType.PYTHON: {
        "pl": ["python", "py", "pip", "venv", "pytest", "skrypt", "moduł"],
        "de": ["python", "py", "pip", "venv", "pytest", "skript", "modul"],
        "en": ["python", "py", "pip", "venv", "pytest", "script", "module"],
    },
    CommandType.CONTEXT: {
        "pl": ["dalej", "kontynuuj", "cofnij", "wstecz", "powtórz", "jeszcze raz", "anuluj", "tak", "nie"],
        "de": ["weiter", "fortfahren", "zurück", "rückgängig", "wiederholen", "nochmal", "abbrechen", "ja", "nein"],
        "en": ["next", "continue", "back", "undo", "repeat", "again", "cancel", "yes", "no"],
    },
    CommandType.QUERY: {
        "pl": ["co", "jaki", "pomoc", "status", "opcje", "możliwości"],
        "de": ["was", "welche", "hilfe", "status", "optionen", "möglichkeiten"],
        "en": ["what", "which", "help", "status", "options", "possibilities"],
    }
}

# Wielojęzyczne mapowania akcji
MULTILANG_ACTION_PATTERNS = {
    "pl": {
        r"(zbuduj|build|make)\s*(projekt|project|all)?": ("MAKE", "build", None),
        r"(uruchom|run)\s+cel\s+(\w+)": ("MAKE", "target", 2),
        r"(wyczyść|clean)": ("MAKE", "clean", None),
        r"(zainstaluj|install)": ("MAKE", "install", None),
        r"(testy|test|tests)": ("MAKE", "test", None),
        r"(uruchom|run|wykonaj|execute)\s+(.+)": ("SHELL", "run", 2),
        r"(lista|list|ls)\s*(plików|files)?": ("SHELL", "ls", None),
        r"(pokaż|show|cat)\s+(.+)": ("SHELL", "cat", 2),
        r"(zatwierdź|commit)\s*(.*)?": ("GIT", "commit", 2),
        r"(wypchnij|push)": ("GIT", "push", None),
        r"(pobierz|pull|fetch)": ("GIT", "pull", None),
        r"(status|stan)": ("GIT", "status", None),
        r"(gałąź|branch)\s+(\w+)?": ("GIT", "branch", 2),
        r"(przełącz|checkout|switch)\s+(\w+)": ("GIT", "checkout", 2),
        r"(zbuduj|build)\s+(obraz|image)\s*(\w+)?": ("DOCKER", "build", 3),
        r"(uruchom|run)\s+(kontener|container)\s*(\w+)?": ("DOCKER", "run", 3),
        r"(zatrzymaj|stop)\s+(kontener|container)\s*(\w+)?": ("DOCKER", "stop", 3),
        r"(kontenery|containers|ps)": ("DOCKER", "ps", None),
        r"(compose)\s+(up|down|restart)": ("DOCKER", "compose", 2),
        r"(uruchom|run)\s+(skrypt|script)\s+(.+)": ("PYTHON", "run", 3),
        r"(pip)\s+(install|uninstall)\s+(.+)": ("PYTHON", "pip", 3),
        r"(pytest|testy|tests)": ("PYTHON", "test", None),
    },
    "de": {
        r"(bauen|build|make)\s*(projekt|project|all)?": ("MAKE", "build", None),
        r"(ausführen|run)\s+ziel\s+(\w+)": ("MAKE", "target", 2),
        r"(säubern|clean)": ("MAKE", "clean", None),
        r"(installieren|install)": ("MAKE", "install", None),
        r"(tests|test)": ("MAKE", "test", None),
        r"(ausführen|run|execute)\s+(.+)": ("SHELL", "run", 2),
        r"(liste|list|ls)\s*(dateien|files)?": ("SHELL", "ls", None),
        r"(zeigen|show|cat)\s+(.+)": ("SHELL", "cat", 2),
        r"(bestätigen|commit)\s*(.*)?": ("GIT", "commit", 2),
        r"(hochladen|push)": ("GIT", "push", None),
        r"(herunterladen|pull|fetch)": ("GIT", "pull", None),
        r"(status|stand)": ("GIT", "status", None),
        r"(zweig|branch)\s+(\w+)?": ("GIT", "branch", 2),
        r"(wechseln|checkout|switch)\s+(\w+)": ("GIT", "checkout", 2),
        r"(bauen|build)\s+(image|bild)\s*(\w+)?": ("DOCKER", "build", 3),
        r"(starten|run)\s+(container)\s*(\w+)?": ("DOCKER", "run", 3),
        r"(stoppen|stop)\s+(container)\s*(\w+)?": ("DOCKER", "stop", 3),
        r"(container|ps)": ("DOCKER", "ps", None),
        r"(compose)\s+(up|down|restart)": ("DOCKER", "compose", 2),
        r"(ausführen|run)\s+(skript|script)\s+(.+)": ("PYTHON", "run", 3),
        r"(pip)\s+(install|uninstall|installieren|deinstallieren)\s+(.+)": ("PYTHON", "pip", 3),
        r"(pytest|tests)": ("PYTHON", "test", None),
    },
    "en": {
        r"(build|make)\s*(project|all)?": ("MAKE", "build", None),
        r"(run)\s+target\s+(\w+)": ("MAKE", "target", 2),
        r"(clean)": ("MAKE", "clean", None),
        r"(install)": ("MAKE", "install", None),
        r"(test|tests)": ("MAKE", "test", None),
        r"(run|execute)\s+(.+)": ("SHELL", "run", 2),
        r"(list|ls)\s*(files)?": ("SHELL", "ls", None),
        r"(show|cat)\s+(.+)": ("SHELL", "cat", 2),
        r"(commit)\s*(.*)?": ("GIT", "commit", 2),
        r"(push)": ("GIT", "push", None),
        r"(pull|fetch)": ("GIT", "pull", None),
        r"(status)": ("GIT", "status", None),
        r"(branch)\s+(\w+)?": ("GIT", "branch", 2),
        r"(checkout|switch)\s+(\w+)": ("GIT", "checkout", 2),
        r"(build)\s+(image)\s*(\w+)?": ("DOCKER", "build", 3),
        r"(run)\s+(container)\s*(\w+)?": ("DOCKER", "run", 3),
        r"(stop)\s+(container)\s*(\w+)?": ("DOCKER", "stop", 3),
        r"(containers|ps)": ("DOCKER", "ps", None),
        r"(compose)\s+(up|down|restart)": ("DOCKER", "compose", 2),
        r"(run)\s+(script)\s+(.+)": ("PYTHON", "run", 3),
        r"(pip)\s+(install|uninstall)\s+(.+)": ("PYTHON", "pip", 3),
        r"(pytest|tests)": ("PYTHON", "test", None),
    }
}

# Wielojęzyczne skróty kontekstowe
MULTILANG_CONTEXT_SHORTCUTS = {
    "pl": {
        "dalej": "next", "kontynuuj": "next", "cofnij": "undo", "wstecz": "undo",
        "powtórz": "repeat", "jeszcze raz": "repeat", "anuluj": "cancel",
        "tak": "confirm", "nie": "deny", "ok": "confirm",
    },
    "de": {
        "weiter": "next", "fortfahren": "next", "zurück": "undo", "rückgängig": "undo",
        "wiederholen": "repeat", "nochmal": "repeat", "abbrechen": "cancel",
        "ja": "confirm", "nein": "deny", "ok": "confirm",
    },
    "en": {
        "next": "next", "continue": "next", "back": "undo", "undo": "undo",
        "repeat": "repeat", "again": "repeat", "cancel": "cancel",
        "yes": "confirm", "no": "deny", "ok": "confirm",
    }
}


class DSLParser:
    """
    Parser DSL dla głosowej nawigacji CLI
    Obsługuje języki: polski, niemiecki, angielski
    
    Obsługuje:
    - Rozpoznawanie intencji z naturalnego języka (PL/DE/EN)
    - Automatyczne wykrywanie języka
    - Skróty kontekstowe
    - Wieloznaczności i sugestie alternatyw
    """
    
    def __init__(self, language: str = "pl"):
        self.language = language.lower()[:2]
        self.last_command: Optional[ParsedCommand] = None
        self.command_history: List[ParsedCommand] = []
        
        # Pobierz mapowania dla aktualnego języka
        self._update_language_mappings()
    
    def _update_language_mappings(self):
        """Aktualizuje mapowania dla aktualnego języka"""
        self.keywords = {}
        for cmd_type, lang_keywords in MULTILANG_KEYWORDS.items():
            self.keywords[cmd_type] = lang_keywords.get(self.language, lang_keywords.get("en", []))
        
        self.action_patterns = MULTILANG_ACTION_PATTERNS.get(
            self.language, 
            MULTILANG_ACTION_PATTERNS["en"]
        )
        
        self.context_shortcuts = MULTILANG_CONTEXT_SHORTCUTS.get(
            self.language,
            MULTILANG_CONTEXT_SHORTCUTS["en"]
        )
    
    def set_language(self, language: str):
        """Zmienia język parsera"""
        self.language = language.lower()[:2]
        self._update_language_mappings()
    
    def detect_language(self, text: str) -> str:
        """
        Próbuje wykryć język z tekstu
        
        Returns:
            Kod języka (pl, de, en)
        """
        text_lower = text.lower()
        
        # Charakterystyczne słowa dla każdego języka
        lang_indicators = {
            "pl": ["zbuduj", "uruchom", "pokaż", "wypchnij", "pobierz", "dalej", "cofnij", "tak", "nie"],
            "de": ["bauen", "ausführen", "zeigen", "hochladen", "herunterladen", "weiter", "zurück", "ja", "nein"],
            "en": ["build", "run", "show", "push", "pull", "next", "back", "yes", "no"],
        }
        
        scores = {lang: 0 for lang in lang_indicators}
        
        for lang, indicators in lang_indicators.items():
            for word in indicators:
                if word in text_lower:
                    scores[lang] += 1
        
        best_lang = max(scores, key=scores.get)
        return best_lang if scores[best_lang] > 0 else self.language
    
    def parse(self, input_text: str, auto_detect_lang: bool = False) -> ParsedCommand:
        """
        Główna metoda parsowania tekstu na komendę DSL
        
        Args:
            input_text: Tekst wejściowy (z STT lub wpisany)
            auto_detect_lang: Czy automatycznie wykryć język
            
        Returns:
            ParsedCommand z rozpoznaną intencją
        """
        # Opcjonalne wykrywanie języka
        detected_lang = self.language
        if auto_detect_lang:
            detected_lang = self.detect_language(input_text)
            if detected_lang != self.language:
                self.set_language(detected_lang)
        
        # Normalizacja wejścia
        normalized = self._normalize(input_text)
        
        # Sprawdź skróty kontekstowe
        if normalized in self.context_shortcuts:
            return self._handle_context_shortcut(normalized, input_text, detected_lang)
        
        # Sprawdź czy to zapytanie
        if self._is_query(normalized):
            return self._parse_query(normalized, input_text, detected_lang)
        
        # Próbuj dopasować do wzorców
        command = self._match_patterns(normalized, input_text, detected_lang)
        if command:
            self._update_history(command)
            return command
        
        # Próbuj rozpoznać typ po słowach kluczowych
        command = self._infer_from_keywords(normalized, input_text, detected_lang)
        if command:
            self._update_history(command)
            return command
        
        # Nie rozpoznano - zwróć jako shell z niską pewnością
        return ParsedCommand(
            type=CommandType.SHELL,
            action="unknown",
            raw_input=input_text,
            confidence=0.3,
            args=[normalized],
            detected_language=detected_lang
        )
    
    def _normalize(self, text: str) -> str:
        """Normalizuje tekst wejściowy"""
        text = text.lower().strip()
        # Usuń interpunkcję końcową
        text = re.sub(r'[.!?]+$', '', text)
        # Zamień wielokrotne spacje na pojedyncze
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _handle_context_shortcut(self, shortcut: str, raw: str, lang: str = "pl") -> ParsedCommand:
        """Obsługuje skróty kontekstowe"""
        action = self.context_shortcuts.get(shortcut, shortcut)
        
        if action == "repeat" and self.last_command:
            # Zwróć kopię ostatniej komendy
            cmd = ParsedCommand(
                type=self.last_command.type,
                action=self.last_command.action,
                target=self.last_command.target,
                args=self.last_command.args.copy(),
                flags=self.last_command.flags.copy(),
                raw_input=raw,
                confidence=0.95,
                detected_language=lang
            )
            return cmd
        
        return ParsedCommand(
            type=CommandType.CONTEXT,
            action=action,
            raw_input=raw,
            confidence=1.0,
            detected_language=lang
        )
    
    def _is_query(self, text: str) -> bool:
        """Sprawdza czy tekst jest zapytaniem"""
        # Wielojęzyczne query starters
        query_starters = {
            "pl": ["co ", "jaki ", "jak ", "gdzie ", "czy ", "pomoc", "?"],
            "de": ["was ", "welche ", "wie ", "wo ", "hilfe", "?"],
            "en": ["what ", "which ", "how ", "where ", "help", "?"],
        }
        
        starters = query_starters.get(self.language, query_starters["en"])
        return any(text.startswith(q) or text.endswith(q) for q in starters)
    
    def _parse_query(self, normalized: str, raw: str, lang: str = "pl") -> ParsedCommand:
        """Parsuje zapytanie"""
        # Wielojęzyczne słowa kluczowe
        options_words = {
            "pl": ["opcje", "możliwości", "co mogę"],
            "de": ["optionen", "möglichkeiten", "was kann"],
            "en": ["options", "possibilities", "what can"],
        }
        status_words = {
            "pl": ["status", "stan"],
            "de": ["status", "stand"],
            "en": ["status", "state"],
        }
        help_words = {
            "pl": ["pomoc"],
            "de": ["hilfe"],
            "en": ["help"],
        }
        
        lang_options = options_words.get(lang, options_words["en"])
        lang_status = status_words.get(lang, status_words["en"])
        lang_help = help_words.get(lang, help_words["en"])
        
        if any(w in normalized for w in lang_options):
            action = "options"
        elif any(w in normalized for w in lang_status):
            action = "status"
        elif any(w in normalized for w in lang_help):
            action = "help"
        else:
            action = "query"
        
        return ParsedCommand(
            type=CommandType.QUERY,
            action=action,
            raw_input=raw,
            confidence=0.9,
            detected_language=lang
        )
    
    def _match_patterns(self, normalized: str, raw: str, lang: str = "pl") -> Optional[ParsedCommand]:
        """Dopasowuje tekst do zdefiniowanych wzorców"""
        for pattern, (cmd_type, action, target_group) in self.action_patterns.items():
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                target = None
                if target_group and len(match.groups()) >= target_group:
                    target = match.group(target_group)
                    if target:
                        target = target.strip()
                
                return ParsedCommand(
                    type=CommandType[cmd_type],
                    action=action,
                    target=target,
                    raw_input=raw,
                    confidence=0.85,
                    detected_language=lang
                )
        return None
    
    def _infer_from_keywords(self, normalized: str, raw: str, lang: str = "pl") -> Optional[ParsedCommand]:
        """Próbuje rozpoznać typ komendy po słowach kluczowych"""
        words = set(normalized.split())
        
        best_match: Optional[Tuple[CommandType, int]] = None
        
        for cmd_type, keywords in self.keywords.items():
            keyword_set = set(keywords)
            overlap = len(words & keyword_set)
            if overlap > 0:
                if best_match is None or overlap > best_match[1]:
                    best_match = (cmd_type, overlap)
        
        if best_match:
            return ParsedCommand(
                type=best_match[0],
                action="inferred",
                raw_input=raw,
                confidence=0.6,
                args=list(words),
                detected_language=lang
            )
        
        return None
    
    def _update_history(self, command: ParsedCommand):
        """Aktualizuje historię komend"""
        self.last_command = command
        self.command_history.append(command)
        # Ogranicz historię do 50 elementów
        if len(self.command_history) > 50:
            self.command_history = self.command_history[-50:]
    
    def get_suggestions(self, partial: str) -> List[str]:
        """
        Zwraca sugestie dla częściowego wejścia
        
        Args:
            partial: Częściowy tekst komendy
            
        Returns:
            Lista sugerowanych uzupełnień
        """
        suggestions = []
        normalized = self._normalize(partial)
        
        # Sugestie na podstawie historii
        for cmd in reversed(self.command_history[-10:]):
            if cmd.raw_input.lower().startswith(normalized):
                suggestions.append(cmd.raw_input)
        
        # Sugestie na podstawie słów kluczowych
        for keywords in self.KEYWORD_MAPPINGS.values():
            for kw in keywords:
                if kw.startswith(normalized):
                    suggestions.append(kw)
        
        return list(dict.fromkeys(suggestions))[:5]  # Unikalne, max 5
