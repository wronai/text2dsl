"""
Text2Make - Warstwa obsługi Makefile

Funkcje:
- Parsowanie celów z Makefile
- Wykonywanie celów
- Analiza zależności
- Sugestie kontekstowe
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
import subprocess
import re
import os


@dataclass
class MakeTarget:
    """Cel w Makefile"""

    name: str
    dependencies: List[str] = field(default_factory=list)
    description: Optional[str] = None
    is_phony: bool = False
    line_number: int = 0


@dataclass
class MakeResult:
    """Wynik wykonania make"""

    success: bool
    output: str
    error: str
    return_code: int
    target: str
    duration_ms: int = 0


class Text2Make:
    """
    Warstwa obsługi Makefile

    Użycie:
        make = Text2Make("/path/to/project")

        # Lista celów
        targets = make.get_targets()

        # Wykonaj cel
        result = make.run("build")

        # Sugestie
        suggestions = make.get_suggestions()
    """

    # Mapowanie poleceń naturalnych na cele
    NATURAL_COMMANDS = {
        "zbuduj": ["build", "all", "compile"],
        "build": ["build", "all", "compile"],
        "testy": ["test", "tests", "check"],
        "test": ["test", "tests", "check"],
        "wyczyść": ["clean", "distclean"],
        "clean": ["clean", "distclean"],
        "zainstaluj": ["install"],
        "install": ["install"],
        "uruchom": ["run", "start", "serve"],
        "run": ["run", "start", "serve"],
        "lint": ["lint", "check", "style"],
        "docs": ["docs", "doc", "documentation"],
    }

    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self.makefile_path: Optional[Path] = None
        self.targets: Dict[str, MakeTarget] = {}
        self.phony_targets: set = set()

        self._find_makefile()
        if self.makefile_path:
            self._parse_makefile()

    def _find_makefile(self):
        """Znajduje Makefile w katalogu"""
        for name in ["Makefile", "makefile", "GNUmakefile"]:
            path = self.working_dir / name
            if path.exists():
                self.makefile_path = path
                break

    def _parse_makefile(self):
        """Parsuje Makefile"""
        if not self.makefile_path:
            return

        try:
            content = self.makefile_path.read_text()
            lines = content.split("\n")

            # Znajdź cele .PHONY
            phony_match = re.search(r"\.PHONY:\s*(.+)", content)
            if phony_match:
                self.phony_targets = set(phony_match.group(1).split())

            current_description = None

            for i, line in enumerate(lines):
                # Komentarz z opisem (przed celem)
                if line.strip().startswith("#"):
                    desc = line.strip("#").strip()
                    if desc and not desc.startswith("!"):
                        current_description = desc
                    continue

                # Cel
                match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)?$", line)
                if match:
                    target_name = match.group(1)
                    deps_str = match.group(2) or ""
                    deps = [d.strip() for d in deps_str.split() if d.strip()]

                    # Pomijaj cele specjalne i zmienne
                    if target_name.startswith(".") or "=" in line:
                        current_description = None
                        continue

                    self.targets[target_name] = MakeTarget(
                        name=target_name,
                        dependencies=deps,
                        description=current_description,
                        is_phony=target_name in self.phony_targets,
                        line_number=i + 1,
                    )
                    current_description = None
        except Exception as e:
            print(f"Błąd parsowania Makefile: {e}")

    def get_targets(self) -> List[MakeTarget]:
        """Zwraca listę celów"""
        return list(self.targets.values())

    def get_target(self, name: str) -> Optional[MakeTarget]:
        """Pobiera cel po nazwie"""
        return self.targets.get(name)

    def resolve_natural_command(self, command: str) -> Optional[str]:
        """
        Tłumaczy naturalne polecenie na cel Makefile

        Args:
            command: Naturalne polecenie (np. "zbuduj")

        Returns:
            Nazwa celu lub None
        """
        command_lower = command.lower()

        # Sprawdź bezpośrednie dopasowanie
        if command_lower in self.targets:
            return command_lower

        # Sprawdź mapowanie
        if command_lower in self.NATURAL_COMMANDS:
            for candidate in self.NATURAL_COMMANDS[command_lower]:
                if candidate in self.targets:
                    return candidate

        # Fuzzy matching
        for target_name in self.targets:
            if command_lower in target_name or target_name in command_lower:
                return target_name

        return None

    def run(
        self,
        target: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
        jobs: Optional[int] = None,
    ) -> MakeResult:
        """
        Wykonuje cel Makefile

        Args:
            target: Nazwa celu (None = domyślny)
            variables: Zmienne do przekazania (VAR=value)
            dry_run: Tylko pokaż co by się wykonało
            jobs: Liczba równoległych zadań (-j)

        Returns:
            MakeResult z wynikiem wykonania
        """
        import time

        start_time = time.time()

        cmd = ["make"]

        if dry_run:
            cmd.append("-n")

        if jobs:
            cmd.extend(["-j", str(jobs)])

        if variables:
            for key, value in variables.items():
                cmd.append(f"{key}={value}")

        if target:
            cmd.append(target)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minut timeout
            )

            duration = int((time.time() - start_time) * 1000)

            return MakeResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr,
                return_code=result.returncode,
                target=target or "default",
                duration_ms=duration,
            )
        except subprocess.TimeoutExpired:
            return MakeResult(
                success=False,
                output="",
                error="Timeout - wykonanie przekroczyło 5 minut",
                return_code=-1,
                target=target or "default",
            )
        except FileNotFoundError:
            return MakeResult(
                success=False,
                output="",
                error="make nie jest zainstalowany",
                return_code=-1,
                target=target or "default",
            )

    def get_suggestions(self, partial: str = "") -> List[Tuple[str, str]]:
        """
        Generuje sugestie celów

        Args:
            partial: Częściowa nazwa celu

        Returns:
            Lista (nazwa, opis) sugestii
        """
        suggestions = []

        for target in self.targets.values():
            if not partial or partial.lower() in target.name.lower():
                desc = target.description or f"Cel: {target.name}"
                suggestions.append((target.name, desc))

        # Sortuj - najpierw phony (częściej używane), potem alfabetycznie
        suggestions.sort(key=lambda x: (0 if x[0] in self.phony_targets else 1, x[0]))

        return suggestions[:10]

    def get_dependency_tree(self, target: str) -> Dict[str, List[str]]:
        """
        Zwraca drzewo zależności dla celu

        Args:
            target: Nazwa celu

        Returns:
            Słownik {cel: [zależności]}
        """
        tree = {}
        visited = set()

        def collect(name: str):
            if name in visited or name not in self.targets:
                return
            visited.add(name)

            t = self.targets[name]
            tree[name] = t.dependencies

            for dep in t.dependencies:
                collect(dep)

        collect(target)
        return tree

    def format_targets_for_voice(self) -> str:
        """Formatuje cele do odczytu głosowego"""
        if not self.targets:
            return "Nie znaleziono celów w Makefile."

        lines = ["Dostępne cele:"]
        for i, target in enumerate(self.get_suggestions()[:5], 1):
            name, desc = target
            lines.append(f"{i}. {name}")

        return " ".join(lines)

    def format_targets_for_display(self) -> str:
        """Formatuje cele do wyświetlenia"""
        if not self.targets:
            return "Brak Makefile lub pusty Makefile."

        lines = ["┌─ Cele Makefile ─────────────────────┐"]
        for name, desc in self.get_suggestions():
            phony = "●" if name in self.phony_targets else "○"
            lines.append(f"│ {phony} {name:15} {desc[:25]}")
        lines.append("└──────────────────────────────────────┘")

        return "\n".join(lines)

    def has_makefile(self) -> bool:
        """Sprawdza czy istnieje Makefile"""
        return self.makefile_path is not None


class MakefileGenerator:
    """Generator Makefile z naturalnego opisu"""

    TEMPLATES = {
        "python": """
.PHONY: all install test lint clean run

all: install test

install:
\tpip install -r requirements.txt

test:
\tpytest tests/

lint:
\tflake8 .
\tmypy .

clean:
\tfind . -type d -name __pycache__ -exec rm -rf {} +
\tfind . -type f -name "*.pyc" -delete

run:
\tpython main.py
""",
        "docker": """
.PHONY: build run stop clean logs

IMAGE_NAME ?= app
CONTAINER_NAME ?= app-container

build:
\tdocker build -t $(IMAGE_NAME) .

run:
\tdocker run -d --name $(CONTAINER_NAME) $(IMAGE_NAME)

stop:
\tdocker stop $(CONTAINER_NAME)
\tdocker rm $(CONTAINER_NAME)

logs:
\tdocker logs -f $(CONTAINER_NAME)

clean: stop
\tdocker rmi $(IMAGE_NAME)
""",
        "basic": """
.PHONY: all build clean test

all: build

build:
\t@echo "Building..."

test:
\t@echo "Running tests..."

clean:
\t@echo "Cleaning..."
""",
    }

    @classmethod
    def generate(cls, project_type: str = "basic") -> str:
        """Generuje Makefile dla typu projektu"""
        return cls.TEMPLATES.get(project_type, cls.TEMPLATES["basic"])
