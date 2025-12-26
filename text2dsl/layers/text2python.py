"""
Text2Python - Warstwa obsługi Python

Funkcje:
- Naturalne polecenia Python
- Zarządzanie środowiskiem wirtualnym
- Pip i zależności
- Uruchamianie skryptów i testów
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import subprocess
import sys
import re
import os


@dataclass
class Package:
    """Informacje o pakiecie"""

    name: str
    version: str
    location: Optional[str] = None


@dataclass
class PythonResult:
    """Wynik operacji Python"""

    success: bool
    output: str
    error: str
    operation: str
    return_code: int = 0


class Text2Python:
    """
    Warstwa obsługi Python

    Użycie:
        py = Text2Python("/path/to/project")

        # Uruchom skrypt
        result = py.run_script("main.py")

        # Naturalne polecenie
        result = py.execute_natural("uruchom testy")
    """

    # Mapowanie naturalnych poleceń
    NATURAL_COMMANDS = {
        "testy": "pytest",
        "tests": "pytest",
        "uruchom testy": "pytest",
        "test": "pytest",
        "lint": "flake8 .",
        "sprawdź styl": "flake8 .",
        "formatuj": "black .",
        "format": "black .",
        "typy": "mypy .",
        "sprawdź typy": "mypy .",
        "zainstaluj": "pip install",
        "install": "pip install",
        "odinstaluj": "pip uninstall",
        "uninstall": "pip uninstall",
        "pakiety": "pip list",
        "lista pakietów": "pip list",
        "zamrożone": "pip freeze",
        "freeze": "pip freeze",
        "wymagania": "pip install -r requirements.txt",
        "requirements": "pip install -r requirements.txt",
        "utwórz venv": "python -m venv venv",
        "aktywuj venv": "source venv/bin/activate",
    }

    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self._venv_path: Optional[Path] = None
        self._python_path: Optional[Path] = None

        self._find_venv()
        self._detect_python()

    def _find_venv(self):
        """Znajduje środowisko wirtualne"""
        for venv_name in ["venv", ".venv", "env", ".env"]:
            venv_path = self.working_dir / venv_name
            python_path = venv_path / "bin" / "python"
            if python_path.exists():
                self._venv_path = venv_path
                self._python_path = python_path
                break

    def _detect_python(self):
        """Wykrywa interpreter Python"""
        if self._python_path is None:
            # Użyj systemowego Python
            self._python_path = Path(sys.executable)

    def _run_python(self, *args: str, timeout: int = 300) -> PythonResult:
        """Wykonuje polecenie Python"""
        cmd = [str(self._python_path)] + list(args)

        env = os.environ.copy()
        if self._venv_path:
            env["VIRTUAL_ENV"] = str(self._venv_path)
            env["PATH"] = f"{self._venv_path / 'bin'}:{env.get('PATH', '')}"

        try:
            result = subprocess.run(
                cmd, cwd=self.working_dir, capture_output=True, text=True, timeout=timeout, env=env
            )

            return PythonResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                operation=" ".join(args),
                return_code=result.returncode,
            )
        except subprocess.TimeoutExpired:
            return PythonResult(
                success=False, output="", error="Timeout", operation=" ".join(args), return_code=-1
            )
        except Exception as e:
            return PythonResult(
                success=False, output="", error=str(e), operation=" ".join(args), return_code=-1
            )

    def _run_pip(self, *args: str, timeout: int = 120) -> PythonResult:
        """Wykonuje polecenie pip"""
        return self._run_python("-m", "pip", *args, timeout=timeout)

    def _run_tool(self, tool: str, *args: str, timeout: int = 300) -> PythonResult:
        """Wykonuje narzędzie Python (pytest, black, etc.)"""
        tool_path = self._venv_path / "bin" / tool if self._venv_path else None

        if tool_path and tool_path.exists():
            cmd = [str(tool_path)] + list(args)
        else:
            cmd = [str(self._python_path), "-m", tool] + list(args)

        env = os.environ.copy()
        if self._venv_path:
            env["VIRTUAL_ENV"] = str(self._venv_path)
            env["PATH"] = f"{self._venv_path / 'bin'}:{env.get('PATH', '')}"

        try:
            result = subprocess.run(
                cmd, cwd=self.working_dir, capture_output=True, text=True, timeout=timeout, env=env
            )

            return PythonResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                operation=f"{tool} {' '.join(args)}",
                return_code=result.returncode,
            )
        except Exception as e:
            return PythonResult(
                success=False,
                output="",
                error=str(e),
                operation=f"{tool} {' '.join(args)}",
                return_code=-1,
            )

    def has_venv(self) -> bool:
        """Sprawdza czy jest aktywne venv"""
        return self._venv_path is not None

    def get_python_version(self) -> str:
        """Pobiera wersję Python"""
        result = self._run_python("--version")
        return result.output if result.success else "unknown"

    def get_packages(self) -> List[Package]:
        """Pobiera listę zainstalowanych pakietów"""
        result = self._run_pip("list", "--format", "json")

        if not result.success:
            return []

        try:
            import json

            data = json.loads(result.output)
            return [Package(name=p["name"], version=p["version"]) for p in data]
        except Exception:
            return []

    def install(self, *packages: str, upgrade: bool = False) -> PythonResult:
        """Instaluje pakiety"""
        args = ["install"]
        if upgrade:
            args.append("--upgrade")
        args.extend(packages)
        return self._run_pip(*args)

    def uninstall(self, *packages: str) -> PythonResult:
        """Odinstalowuje pakiety"""
        return self._run_pip("uninstall", "-y", *packages)

    def install_requirements(self, file: str = "requirements.txt") -> PythonResult:
        """Instaluje zależności z pliku"""
        return self._run_pip("install", "-r", file)

    def freeze(self, file: Optional[str] = None) -> PythonResult:
        """Eksportuje zależności"""
        result = self._run_pip("freeze")

        if result.success and file:
            try:
                (self.working_dir / file).write_text(result.output)
            except Exception as e:
                result.error = str(e)

        return result

    def create_venv(self, name: str = "venv") -> PythonResult:
        """Tworzy środowisko wirtualne"""
        venv_path = self.working_dir / name

        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            cwd=self.working_dir,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            self._venv_path = venv_path
            self._python_path = venv_path / "bin" / "python"

        return PythonResult(
            success=result.returncode == 0,
            output=result.stdout,
            error=result.stderr,
            operation=f"venv {name}",
            return_code=result.returncode,
        )

    def run_script(self, script: str, *args: str) -> PythonResult:
        """Uruchamia skrypt Python"""
        return self._run_python(script, *args)

    def run_module(self, module: str, *args: str) -> PythonResult:
        """Uruchamia moduł Python"""
        return self._run_python("-m", module, *args)

    def pytest(self, *args: str) -> PythonResult:
        """Uruchamia pytest"""
        return self._run_tool("pytest", *args)

    def black(self, *paths: str) -> PythonResult:
        """Uruchamia black"""
        if not paths:
            paths = (".",)
        return self._run_tool("black", *paths)

    def flake8(self, *paths: str) -> PythonResult:
        """Uruchamia flake8"""
        if not paths:
            paths = (".",)
        return self._run_tool("flake8", *paths)

    def mypy(self, *paths: str) -> PythonResult:
        """Uruchamia mypy"""
        if not paths:
            paths = (".",)
        return self._run_tool("mypy", *paths)

    def execute_natural(self, natural_command: str) -> PythonResult:
        """Wykonuje naturalne polecenie Python"""
        natural_lower = natural_command.lower().strip()

        # Proste mapowania
        for key, cmd in self.NATURAL_COMMANDS.items():
            if natural_lower == key:
                parts = cmd.split()
                if parts[0] == "pip":
                    return self._run_pip(*parts[1:])
                elif parts[0] == "pytest":
                    return self.pytest()
                elif parts[0] == "black":
                    return self.black()
                elif parts[0] == "flake8":
                    return self.flake8()
                elif parts[0] == "mypy":
                    return self.mypy()
                else:
                    return self._run_python(*parts)

        # Złożone polecenia
        patterns = [
            (r"uruchom (.+\.py)", lambda m: self.run_script(m.group(1))),
            (r"run (.+\.py)", lambda m: self.run_script(m.group(1))),
            (r"zainstaluj (.+)", lambda m: self.install(*m.group(1).split())),
            (r"install (.+)", lambda m: self.install(*m.group(1).split())),
            (r"odinstaluj (.+)", lambda m: self.uninstall(*m.group(1).split())),
            (r"testy (.+)", lambda m: self.pytest(m.group(1))),
            (r"formatuj (.+)", lambda m: self.black(m.group(1))),
        ]

        for pattern, handler in patterns:
            match = re.match(pattern, natural_lower)
            if match:
                return handler(match)

        # Fallback - spróbuj wykonać jako polecenie Python
        if natural_lower.endswith(".py"):
            return self.run_script(natural_lower)

        return PythonResult(
            success=False,
            output="",
            error=f"Nie rozpoznano polecenia: {natural_command}",
            operation="parse",
            return_code=-1,
        )

    def get_suggestions(self, partial: str = "") -> List[Tuple[str, str]]:
        """Generuje sugestie"""
        suggestions = []

        # Kontekstowe
        if not self.has_venv():
            suggestions.append(("utwórz venv", "python -m venv venv"))
        else:
            suggestions.append(("aktywne venv", str(self._venv_path)))

        # Pliki w projekcie
        if (self.working_dir / "requirements.txt").exists():
            suggestions.append(("zainstaluj wymagania", "pip install -r requirements.txt"))

        if (self.working_dir / "setup.py").exists() or (
            self.working_dir / "pyproject.toml"
        ).exists():
            suggestions.append(("zainstaluj projekt", "pip install -e ."))

        if (self.working_dir / "tests").is_dir() or list(self.working_dir.glob("test_*.py")):
            suggestions.append(("uruchom testy", "pytest"))

        # Ogólne
        for natural, bash in self.NATURAL_COMMANDS.items():
            if not partial or partial.lower() in natural.lower():
                suggestions.append((natural, bash))

        return suggestions[:10]

    def format_packages_for_voice(self) -> str:
        """Formatuje pakiety do odczytu głosowego"""
        packages = self.get_packages()
        if not packages:
            return "Brak zainstalowanych pakietów."

        return f"Zainstalowano {len(packages)} pakietów."

    def format_packages_for_display(self) -> str:
        """Formatuje pakiety do wyświetlenia"""
        packages = self.get_packages()
        if not packages:
            return "Brak pakietów."

        lines = [
            f"┌─ Python {self.get_python_version()} ─────────────",
            f"│ venv: {'✓ ' + str(self._venv_path.name) if self._venv_path else '✗'}",
            "├─ Pakiety ────────────────────────────",
        ]

        for pkg in packages[:10]:
            lines.append(f"│ {pkg.name:20} {pkg.version}")

        if len(packages) > 10:
            lines.append(f"│ ... i {len(packages) - 10} więcej")

        lines.append("└───────────────────────────────────────")
        return "\n".join(lines)
