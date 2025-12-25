"""
Text2Shell - Warstwa obsługi poleceń shell

Funkcje:
- Tłumaczenie naturalnych poleceń na bash
- Bezpieczne wykonywanie komend
- Historia i aliasy
- Sugestie kontekstowe
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Callable
from pathlib import Path
import subprocess
import shlex
import re
import os


@dataclass
class ShellResult:
    """Wynik wykonania komendy shell"""
    success: bool
    output: str
    error: str
    return_code: int
    command: str
    duration_ms: int = 0


@dataclass
class ShellAlias:
    """Alias komendy"""
    name: str
    command: str
    description: Optional[str] = None


class Text2Shell:
    """
    Warstwa obsługi poleceń shell
    
    Bezpiecznie wykonuje komendy i tłumaczy naturalny język na bash.
    """
    
    # Mapowanie naturalnych poleceń na bash
    NATURAL_COMMANDS = {
        "pokaż pliki": "ls -la",
        "lista plików": "ls -la",
        "pokaż katalog": "pwd",
        "gdzie jestem": "pwd",
        "utwórz katalog": "mkdir -p",
        "usuń plik": "rm",
        "kopiuj": "cp",
        "przenieś": "mv",
        "znajdź": "find . -name",
        "pokaż procesy": "ps aux",
        "miejsce na dysku": "df -h",
        "pamięć": "free -h",
        "szukaj w plikach": "grep -r",
        "pokaż plik": "cat",
        "ostatnie linie": "tail -n 20",
    }
    
    # Niebezpieczne wzorce (blokowane)
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/\s*$",
        r"rm\s+-rf\s+/\*",
        r":\(\)\{\s*:\|:\s*&\s*\};:",
        r"dd\s+if=/dev/zero\s+of=/dev/sd",
    ]
    
    def __init__(self, working_dir: Optional[str] = None, timeout: int = 60):
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self.timeout = timeout
        self.history: List[ShellResult] = []
        self.aliases: Dict[str, ShellAlias] = {}
        self.env: Dict[str, str] = {}
        self._confirm_callback: Optional[Callable[[str], bool]] = None
        
    def _is_dangerous(self, command: str) -> bool:
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                return True
        return False
    
    def run(self, command: str, capture: bool = True, shell: bool = True) -> ShellResult:
        """Wykonuje komendę shell"""
        import time
        
        if self._is_dangerous(command):
            return ShellResult(
                success=False,
                output="",
                error="Komenda zablokowana ze względów bezpieczeństwa",
                return_code=-1,
                command=command
            )
        
        # Rozwiń aliasy
        words = command.split()
        if words and words[0] in self.aliases:
            words[0] = self.aliases[words[0]].command
            command = " ".join(words)
        
        run_env = os.environ.copy()
        run_env.update(self.env)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                cwd=self.working_dir,
                capture_output=capture,
                text=True,
                timeout=self.timeout,
                env=run_env
            )
            
            duration = int((time.time() - start_time) * 1000)
            
            shell_result = ShellResult(
                success=result.returncode == 0,
                output=result.stdout if capture else "",
                error=result.stderr if capture else "",
                return_code=result.returncode,
                command=command,
                duration_ms=duration
            )
            
            self.history.append(shell_result)
            return shell_result
            
        except subprocess.TimeoutExpired:
            return ShellResult(
                success=False, output="", 
                error=f"Timeout - przekroczono {self.timeout}s",
                return_code=-1, command=command
            )
        except Exception as e:
            return ShellResult(
                success=False, output="", error=str(e),
                return_code=-1, command=command
            )
    
    def translate_to_bash(self, natural: str) -> str:
        """Tłumaczy naturalne polecenie na bash"""
        natural_lower = natural.lower().strip()
        
        if natural_lower in self.NATURAL_COMMANDS:
            return self.NATURAL_COMMANDS[natural_lower]
        
        for key, cmd in self.NATURAL_COMMANDS.items():
            if key in natural_lower:
                rest = natural_lower.replace(key, "").strip()
                if rest:
                    return f"{cmd} {rest}"
                return cmd
        
        return natural
    
    def execute_natural(self, natural_command: str) -> ShellResult:
        """Wykonuje naturalne polecenie"""
        bash_command = self.translate_to_bash(natural_command)
        return self.run(bash_command)
    
    def add_alias(self, name: str, command: str, description: Optional[str] = None):
        self.aliases[name] = ShellAlias(name, command, description)
    
    def cd(self, path: str) -> bool:
        new_path = Path(path)
        if not new_path.is_absolute():
            new_path = self.working_dir / new_path
        new_path = new_path.resolve()
        
        if new_path.is_dir():
            self.working_dir = new_path
            return True
        return False
    
    def pwd(self) -> str:
        return str(self.working_dir)
    
    def get_suggestions(self, partial: str = "") -> List[Tuple[str, str]]:
        suggestions = []
        
        for result in reversed(self.history[-20:]):
            if result.success and (not partial or partial.lower() in result.command.lower()):
                suggestions.append((result.command, "z historii"))
        
        for natural, bash in self.NATURAL_COMMANDS.items():
            if not partial or partial.lower() in natural.lower():
                suggestions.append((natural, bash))
        
        seen = set()
        unique = []
        for cmd, desc in suggestions:
            if cmd not in seen:
                seen.add(cmd)
                unique.append((cmd, desc))
        
        return unique[:10]
    
    def format_result_for_voice(self, result: ShellResult) -> str:
        if result.success:
            if result.output:
                lines = result.output.strip().split('\n')
                if len(lines) > 3:
                    return f"Wykonano pomyślnie. {lines[0]}... i {len(lines)-1} więcej linii."
                return f"Wykonano pomyślnie. {result.output[:200]}"
            return "Wykonano pomyślnie."
        return f"Błąd: {result.error[:100]}"
    
    def format_result_for_display(self, result: ShellResult) -> str:
        status = "✓" if result.success else "✗"
        lines = [
            f"┌─ {status} {result.command[:40]} ─────────────",
            f"│ Czas: {result.duration_ms}ms | Kod: {result.return_code}",
        ]
        
        if result.output:
            for line in result.output.strip().split('\n')[:5]:
                lines.append(f"│ {line[:60]}")
        
        if result.error:
            lines.append(f"│ ⚠ {result.error[:60]}")
        
        lines.append("└────────────────────────────────────────")
        return "\n".join(lines)
