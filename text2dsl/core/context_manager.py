"""
Context Manager - Zarządzanie kontekstem rozmowy i stanem sesji

Przechowuje:
- Aktualny katalog roboczy
- Aktywny projekt/Makefile
- Historię operacji
- Stan kontenerów Docker
- Stan repozytorium Git
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set
from pathlib import Path
from datetime import datetime
import json
import os


@dataclass
class ProjectContext:
    """Kontekst projektu"""

    path: Path
    name: str
    has_makefile: bool = False
    has_dockerfile: bool = False
    has_docker_compose: bool = False
    has_git: bool = False
    has_python: bool = False
    makefile_targets: List[str] = field(default_factory=list)
    git_branch: Optional[str] = None
    docker_services: List[str] = field(default_factory=list)
    python_venv: Optional[str] = None

    @classmethod
    def from_path(cls, path: Path) -> "ProjectContext":
        """Wykrywa kontekst projektu z podanej ścieżki"""
        path = Path(path).resolve()
        name = path.name

        ctx = cls(path=path, name=name)

        # Sprawdź Makefile
        makefile = path / "Makefile"
        if makefile.exists():
            ctx.has_makefile = True
            ctx.makefile_targets = cls._parse_makefile_targets(makefile)

        # Sprawdź Dockerfile
        ctx.has_dockerfile = (path / "Dockerfile").exists()

        # Sprawdź docker-compose
        for compose_file in [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]:
            if (path / compose_file).exists():
                ctx.has_docker_compose = True
                ctx.docker_services = cls._parse_compose_services(path / compose_file)
                break

        # Sprawdź Git
        ctx.has_git = (path / ".git").exists()
        if ctx.has_git:
            ctx.git_branch = cls._get_git_branch(path)

        # Sprawdź Python
        ctx.has_python = any(
            [
                (path / "setup.py").exists(),
                (path / "pyproject.toml").exists(),
                (path / "requirements.txt").exists(),
            ]
        )

        # Sprawdź venv
        for venv_dir in ["venv", ".venv", "env", ".env"]:
            if (path / venv_dir / "bin" / "python").exists():
                ctx.python_venv = str(path / venv_dir)
                break

        return ctx

    @staticmethod
    def _parse_makefile_targets(makefile: Path) -> List[str]:
        """Parsuje cele z Makefile"""
        targets = []
        try:
            with open(makefile, "r") as f:
                for line in f:
                    # Szukaj linii zaczynających się od nazwy celu
                    if ":" in line and not line.startswith("\t") and not line.startswith(" "):
                        target = line.split(":")[0].strip()
                        # Pomijaj cele specjalne i zmienne
                        if target and not target.startswith(".") and "=" not in target:
                            targets.append(target)
        except Exception:
            pass
        return targets

    @staticmethod
    def _parse_compose_services(compose_file: Path) -> List[str]:
        """Parsuje serwisy z docker-compose"""
        services = []
        try:
            import yaml

            with open(compose_file, "r") as f:
                data = yaml.safe_load(f)
                if data and "services" in data:
                    services = list(data["services"].keys())
        except Exception:
            # Prosty fallback bez yaml
            try:
                with open(compose_file, "r") as f:
                    in_services = False
                    for line in f:
                        if line.strip() == "services:":
                            in_services = True
                            continue
                        if in_services:
                            if line.startswith("  ") and line[2] != " " and ":" in line:
                                service = line.split(":")[0].strip()
                                services.append(service)
                            elif not line.startswith(" ") and line.strip():
                                break
            except Exception:
                pass
        return services

    @staticmethod
    def _get_git_branch(path: Path) -> Optional[str]:
        """Pobiera aktualną gałąź Git"""
        try:
            head_file = path / ".git" / "HEAD"
            if head_file.exists():
                content = head_file.read_text().strip()
                if content.startswith("ref: refs/heads/"):
                    return content.replace("ref: refs/heads/", "")
        except Exception:
            pass
        return None


@dataclass
class ConversationState:
    """Stan pojedynczej rozmowy/sesji"""

    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    command_count: int = 0
    last_command_type: Optional[str] = None
    last_target: Optional[str] = None
    pending_confirmation: Optional[Dict[str, Any]] = None
    variables: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Wynik wykonania komendy"""

    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    duration_ms: int = 0
    command: str = ""


class ContextManager:
    """
    Menedżer kontekstu - zarządza stanem sesji i projektu

    Funkcje:
    - Automatyczne wykrywanie typu projektu
    - Śledzenie stanu konwersacji
    - Kontekstowe podpowiedzi
    - Historia operacji
    """

    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self.project: Optional[ProjectContext] = None
        self.state = ConversationState()
        self.execution_history: List[ExecutionResult] = []

        # Automatyczne wykrycie projektu
        self.refresh_project_context()

    def refresh_project_context(self):
        """Odświeża kontekst projektu"""
        self.project = ProjectContext.from_path(self.working_dir)

    def change_directory(self, path: str) -> bool:
        """Zmienia katalog roboczy"""
        new_path = Path(path)
        if not new_path.is_absolute():
            new_path = self.working_dir / new_path
        new_path = new_path.resolve()

        if new_path.is_dir():
            self.working_dir = new_path
            self.refresh_project_context()
            return True
        return False

    def get_contextual_options(self) -> Dict[str, List[str]]:
        """
        Zwraca kontekstowe opcje na podstawie aktualnego stanu

        Returns:
            Słownik z kategoriami i dostępnymi opcjami
        """
        options: Dict[str, List[str]] = {}

        if not self.project:
            return {"general": ["cd <katalog>", "pwd", "ls"]}

        # Opcje Make
        if self.project.has_makefile:
            options["make"] = [f"make {t}" for t in self.project.makefile_targets[:5]]

        # Opcje Git
        if self.project.has_git:
            git_opts = ["status", "pull", "push", "commit"]
            if self.project.git_branch:
                git_opts.insert(0, f"branch: {self.project.git_branch}")
            options["git"] = git_opts

        # Opcje Docker
        if self.project.has_dockerfile or self.project.has_docker_compose:
            docker_opts = []
            if self.project.has_dockerfile:
                docker_opts.extend(["docker build", "docker run"])
            if self.project.has_docker_compose:
                docker_opts.extend(["compose up", "compose down"])
                for svc in self.project.docker_services[:3]:
                    docker_opts.append(f"compose logs {svc}")
            options["docker"] = docker_opts

        # Opcje Python
        if self.project.has_python:
            py_opts = ["pytest", "pip install -r requirements.txt"]
            if self.project.python_venv:
                py_opts.insert(0, "venv: aktywne")
            options["python"] = py_opts

        # Opcje kontekstowe na podstawie ostatniej akcji
        if self.state.last_command_type:
            if self.state.last_command_type == "MAKE" and self.state.last_target:
                options["kontynuacja"] = [
                    f"powtórz {self.state.last_target}",
                    "następny cel",
                    "wyczyść i zbuduj",
                ]
            elif self.state.last_command_type == "GIT":
                options["kontynuacja"] = ["push", "status", "log"]

        return options

    def get_smart_suggestions(self, partial_input: str = "") -> List[str]:
        """
        Generuje inteligentne sugestie na podstawie kontekstu

        Args:
            partial_input: Częściowe wejście użytkownika

        Returns:
            Lista sugestii posortowana wg relevancji
        """
        suggestions = []

        # Sugestie na podstawie ostatniej operacji
        if self.execution_history:
            last = self.execution_history[-1]
            if not last.success:
                suggestions.append("powtórz ostatnią komendę")
                suggestions.append("pokaż błąd")
            else:
                suggestions.append("dalej")

        # Sugestie specyficzne dla projektu
        if self.project:
            if self.project.has_makefile and self.project.makefile_targets:
                suggestions.append(f"zbuduj (make {self.project.makefile_targets[0]})")

            if self.project.has_git:
                suggestions.append("sprawdź status git")

            if self.project.has_docker_compose:
                suggestions.append("uruchom kontenery")

        # Filtruj po częściowym wejściu
        if partial_input:
            partial_lower = partial_input.lower()
            suggestions = [s for s in suggestions if partial_lower in s.lower()]

        return suggestions[:5]

    def update_state(self, command_type: str, target: Optional[str] = None):
        """Aktualizuje stan konwersacji"""
        self.state.last_activity = datetime.now()
        self.state.command_count += 1
        self.state.last_command_type = command_type
        self.state.last_target = target

    def add_execution_result(self, result: ExecutionResult):
        """Dodaje wynik wykonania do historii"""
        self.execution_history.append(result)
        # Ogranicz historię
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-100:]

    def set_pending_confirmation(self, action: str, details: Dict[str, Any]):
        """Ustawia akcję oczekującą na potwierdzenie"""
        self.state.pending_confirmation = {
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }

    def clear_pending_confirmation(self):
        """Czyści oczekujące potwierdzenie"""
        self.state.pending_confirmation = None

    def get_pending_confirmation(self) -> Optional[Dict[str, Any]]:
        """Pobiera oczekujące potwierdzenie"""
        return self.state.pending_confirmation

    def set_variable(self, name: str, value: Any):
        """Ustawia zmienną sesji"""
        self.state.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Pobiera zmienną sesji"""
        return self.state.variables.get(name, default)

    def to_dict(self) -> Dict[str, Any]:
        """Serializuje kontekst do słownika"""
        return {
            "working_dir": str(self.working_dir),
            "project": {
                "name": self.project.name if self.project else None,
                "has_makefile": self.project.has_makefile if self.project else False,
                "has_git": self.project.has_git if self.project else False,
                "has_docker": self.project.has_dockerfile if self.project else False,
                "has_python": self.project.has_python if self.project else False,
            },
            "state": {
                "command_count": self.state.command_count,
                "last_command": self.state.last_command_type,
            },
        }
