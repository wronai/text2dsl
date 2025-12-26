"""
Text2Docker - Warstwa obsługi Docker

Funkcje:
- Naturalne polecenia Docker
- Zarządzanie kontenerami i obrazami
- Docker Compose
- Sugestie kontekstowe
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import subprocess
import json
import re
import os


@dataclass
class Container:
    """Informacje o kontenerze"""

    id: str
    name: str
    image: str
    status: str
    ports: str = ""
    created: str = ""


@dataclass
class Image:
    """Informacje o obrazie"""

    id: str
    repository: str
    tag: str
    size: str
    created: str


@dataclass
class DockerResult:
    """Wynik operacji Docker"""

    success: bool
    output: str
    error: str
    operation: str


class Text2Docker:
    """
    Warstwa obsługi Docker

    Użycie:
        docker = Text2Docker("/path/to/project")

        # Lista kontenerów
        containers = docker.get_containers()

        # Naturalne polecenie
        result = docker.execute_natural("uruchom kontenery")
    """

    # Mapowanie naturalnych poleceń
    NATURAL_COMMANDS = {
        "kontenery": "docker ps -a",
        "containers": "docker ps -a",
        "pokaż kontenery": "docker ps -a",
        "działające kontenery": "docker ps",
        "obrazy": "docker images",
        "images": "docker images",
        "pokaż obrazy": "docker images",
        "zbuduj": "docker build",
        "build": "docker build",
        "uruchom": "docker run",
        "run": "docker run",
        "zatrzymaj": "docker stop",
        "stop": "docker stop",
        "usuń kontener": "docker rm",
        "usuń obraz": "docker rmi",
        "logi": "docker logs",
        "logs": "docker logs",
        # Compose
        "compose up": "docker compose up -d",
        "uruchom serwisy": "docker compose up -d",
        "compose down": "docker compose down",
        "zatrzymaj serwisy": "docker compose down",
        "compose logs": "docker compose logs -f",
        "logi serwisów": "docker compose logs -f",
        "compose restart": "docker compose restart",
        "restartuj serwisy": "docker compose restart",
        "compose ps": "docker compose ps",
        "status serwisów": "docker compose ps",
    }

    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self._has_dockerfile = (self.working_dir / "Dockerfile").exists()
        self._compose_file = self._find_compose_file()

    def _find_compose_file(self) -> Optional[Path]:
        """Znajduje plik docker-compose"""
        for name in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]:
            path = self.working_dir / name
            if path.exists():
                return path
        return None

    def _run_docker(self, *args: str, timeout: int = 120) -> DockerResult:
        """Wykonuje polecenie docker"""
        cmd = ["docker"] + list(args)

        try:
            result = subprocess.run(
                cmd, cwd=self.working_dir, capture_output=True, text=True, timeout=timeout
            )

            return DockerResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                operation=" ".join(args),
            )
        except subprocess.TimeoutExpired:
            return DockerResult(success=False, output="", error="Timeout", operation=" ".join(args))
        except FileNotFoundError:
            return DockerResult(
                success=False,
                output="",
                error="Docker nie jest zainstalowany",
                operation=" ".join(args),
            )
        except Exception as e:
            return DockerResult(success=False, output="", error=str(e), operation=" ".join(args))

    def _run_compose(self, *args: str, timeout: int = 120) -> DockerResult:
        """Wykonuje polecenie docker compose"""
        cmd = ["docker", "compose"] + list(args)

        try:
            result = subprocess.run(
                cmd, cwd=self.working_dir, capture_output=True, text=True, timeout=timeout
            )

            return DockerResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                operation="compose " + " ".join(args),
            )
        except Exception as e:
            return DockerResult(
                success=False, output="", error=str(e), operation="compose " + " ".join(args)
            )

    def has_docker(self) -> bool:
        """Sprawdza czy Docker jest dostępny"""
        result = self._run_docker("version", "--format", "{{.Server.Version}}")
        return result.success

    def has_dockerfile(self) -> bool:
        """Sprawdza czy istnieje Dockerfile"""
        return self._has_dockerfile

    def has_compose(self) -> bool:
        """Sprawdza czy istnieje docker-compose"""
        return self._compose_file is not None

    def get_containers(self, all: bool = True) -> List[Container]:
        """Pobiera listę kontenerów"""
        args = [
            "ps",
            "--format",
            "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.CreatedAt}}",
        ]
        if all:
            args.insert(1, "-a")

        result = self._run_docker(*args)
        if not result.success:
            return []

        containers = []
        for line in result.output.split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    containers.append(
                        Container(
                            id=parts[0][:12],
                            name=parts[1],
                            image=parts[2],
                            status=parts[3],
                            ports=parts[4] if len(parts) > 4 else "",
                            created=parts[5] if len(parts) > 5 else "",
                        )
                    )

        return containers

    def get_images(self) -> List[Image]:
        """Pobiera listę obrazów"""
        result = self._run_docker(
            "images", "--format", "{{.ID}}|{{.Repository}}|{{.Tag}}|{{.Size}}|{{.CreatedAt}}"
        )

        if not result.success:
            return []

        images = []
        for line in result.output.split("\n"):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 4:
                    images.append(
                        Image(
                            id=parts[0][:12],
                            repository=parts[1],
                            tag=parts[2],
                            size=parts[3],
                            created=parts[4] if len(parts) > 4 else "",
                        )
                    )

        return images

    def get_compose_services(self) -> List[str]:
        """Pobiera listę serwisów z docker-compose"""
        if not self._compose_file:
            return []

        result = self._run_compose("config", "--services")
        if result.success:
            return [s.strip() for s in result.output.split("\n") if s.strip()]
        return []

    def build(self, tag: str = "app", dockerfile: Optional[str] = None) -> DockerResult:
        """Buduje obraz Docker"""
        args = ["build", "-t", tag]
        if dockerfile:
            args.extend(["-f", dockerfile])
        args.append(".")

        return self._run_docker(*args, timeout=600)

    def run(
        self,
        image: str,
        name: Optional[str] = None,
        detach: bool = True,
        ports: Optional[Dict[int, int]] = None,
        volumes: Optional[Dict[str, str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> DockerResult:
        """Uruchamia kontener"""
        args = ["run"]

        if detach:
            args.append("-d")

        if name:
            args.extend(["--name", name])

        if ports:
            for host, container in ports.items():
                args.extend(["-p", f"{host}:{container}"])

        if volumes:
            for host_path, container_path in volumes.items():
                args.extend(["-v", f"{host_path}:{container_path}"])

        if env:
            for key, value in env.items():
                args.extend(["-e", f"{key}={value}"])

        args.append(image)
        return self._run_docker(*args)

    def stop(self, container: str) -> DockerResult:
        """Zatrzymuje kontener"""
        return self._run_docker("stop", container)

    def remove(self, container: str, force: bool = False) -> DockerResult:
        """Usuwa kontener"""
        if force:
            return self._run_docker("rm", "-f", container)
        return self._run_docker("rm", container)

    def logs(self, container: str, tail: int = 100) -> DockerResult:
        """Pobiera logi kontenera"""
        return self._run_docker("logs", "--tail", str(tail), container)

    def compose_up(self, detach: bool = True, services: Optional[List[str]] = None) -> DockerResult:
        """Uruchamia serwisy compose"""
        args = ["up"]
        if detach:
            args.append("-d")
        if services:
            args.extend(services)
        return self._run_compose(*args)

    def compose_down(self, volumes: bool = False) -> DockerResult:
        """Zatrzymuje serwisy compose"""
        args = ["down"]
        if volumes:
            args.append("-v")
        return self._run_compose(*args)

    def compose_logs(self, service: Optional[str] = None, tail: int = 100) -> DockerResult:
        """Pobiera logi compose"""
        args = ["logs", "--tail", str(tail)]
        if service:
            args.append(service)
        return self._run_compose(*args)

    def execute_natural(self, natural_command: str) -> DockerResult:
        """Wykonuje naturalne polecenie Docker"""
        natural_lower = natural_command.lower().strip()

        # Compose commands
        if self.has_compose():
            if any(kw in natural_lower for kw in ["compose", "serwisy", "services"]):
                if "up" in natural_lower or "uruchom" in natural_lower:
                    return self.compose_up()
                if "down" in natural_lower or "zatrzymaj" in natural_lower:
                    return self.compose_down()
                if "log" in natural_lower:
                    return self.compose_logs()
                if "restart" in natural_lower:
                    return self._run_compose("restart")
                if "ps" in natural_lower or "status" in natural_lower:
                    return self._run_compose("ps")

        # Proste mapowania
        for key, cmd in self.NATURAL_COMMANDS.items():
            if natural_lower == key or natural_lower.startswith(key + " "):
                cmd_parts = cmd.replace("docker ", "").split()
                rest = natural_lower.replace(key, "").strip()
                if rest:
                    cmd_parts.append(rest)

                if "compose" in cmd:
                    return self._run_compose(*cmd_parts[1:])
                return self._run_docker(*cmd_parts)

        # Złożone polecenia
        patterns = [
            (r"zbuduj obraz (.+)", lambda m: self.build(m.group(1))),
            (r"uruchom kontener (.+)", lambda m: self.run(m.group(1))),
            (r"zatrzymaj kontener (.+)", lambda m: self.stop(m.group(1))),
            (r"usuń kontener (.+)", lambda m: self.remove(m.group(1))),
            (r"logi kontenera (.+)", lambda m: self.logs(m.group(1))),
        ]

        for pattern, handler in patterns:
            match = re.match(pattern, natural_lower)
            if match:
                return handler(match)

        return DockerResult(
            success=False,
            output="",
            error=f"Nie rozpoznano polecenia: {natural_command}",
            operation="parse",
        )

    def get_suggestions(self, partial: str = "") -> List[Tuple[str, str]]:
        """Generuje sugestie"""
        suggestions = []

        # Kontekstowe
        if self.has_compose():
            services = self.get_compose_services()
            suggestions.append(("uruchom serwisy", "docker compose up -d"))
            suggestions.append(("zatrzymaj serwisy", "docker compose down"))
            for svc in services[:3]:
                suggestions.append((f"logi {svc}", f"docker compose logs {svc}"))

        if self.has_dockerfile():
            suggestions.append(("zbuduj obraz", "docker build -t app ."))

        containers = self.get_containers()
        for c in containers[:3]:
            if "Up" in c.status:
                suggestions.append((f"zatrzymaj {c.name}", f"docker stop {c.name}"))
                suggestions.append((f"logi {c.name}", f"docker logs {c.name}"))
            else:
                suggestions.append((f"uruchom {c.name}", f"docker start {c.name}"))

        # Filtruj
        if partial:
            suggestions = [(n, c) for n, c in suggestions if partial.lower() in n.lower()]

        return suggestions[:10]

    def format_containers_for_voice(self) -> str:
        """Formatuje kontenery do odczytu głosowego"""
        containers = self.get_containers()
        if not containers:
            return "Brak kontenerów."

        running = [c for c in containers if "Up" in c.status]
        stopped = [c for c in containers if "Up" not in c.status]

        parts = []
        if running:
            parts.append(f"{len(running)} działających kontenerów")
        if stopped:
            parts.append(f"{len(stopped)} zatrzymanych")

        return ". ".join(parts) + "."

    def format_containers_for_display(self) -> str:
        """Formatuje kontenery do wyświetlenia"""
        containers = self.get_containers()
        if not containers:
            return "Brak kontenerów Docker."

        lines = ["┌─ Kontenery Docker ──────────────────"]
        for c in containers[:5]:
            status = "●" if "Up" in c.status else "○"
            lines.append(f"│ {status} {c.name[:15]:15} {c.image[:20]:20}")
        lines.append("└─────────────────────────────────────")

        return "\n".join(lines)
