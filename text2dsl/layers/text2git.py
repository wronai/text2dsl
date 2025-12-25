"""
Text2Git - Warstwa obsługi Git

Funkcje:
- Naturalne polecenia Git
- Status i historia
- Operacje na gałęziach
- Sugestie kontekstowe
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from pathlib import Path
import subprocess
import re
import os


@dataclass
class GitStatus:
    """Status repozytorium Git"""
    branch: str
    is_clean: bool
    staged: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


@dataclass
class GitCommit:
    """Informacje o commit"""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str


@dataclass
class GitResult:
    """Wynik operacji Git"""
    success: bool
    output: str
    error: str
    operation: str


class Text2Git:
    """
    Warstwa obsługi Git
    
    Użycie:
        git = Text2Git("/path/to/repo")
        
        # Status
        status = git.get_status()
        
        # Naturalne polecenie
        result = git.execute_natural("zatwierdź wszystkie zmiany")
    """
    
    # Mapowanie naturalnych poleceń
    NATURAL_COMMANDS = {
        "status": "git status",
        "stan": "git status",
        "sprawdź status": "git status",
        "pobierz": "git pull",
        "pull": "git pull",
        "wypchnij": "git push",
        "push": "git push",
        "zatwierdź": "git commit",
        "commit": "git commit",
        "dodaj": "git add",
        "add": "git add",
        "dodaj wszystko": "git add -A",
        "gałęzie": "git branch -a",
        "branches": "git branch -a",
        "historia": "git log --oneline -10",
        "log": "git log --oneline -10",
        "różnice": "git diff",
        "diff": "git diff",
        "cofnij": "git checkout --",
        "reset": "git reset",
        "stash": "git stash",
        "schowaj": "git stash",
        "odłóż": "git stash",
    }
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = Path(working_dir or os.getcwd()).resolve()
        self._git_dir: Optional[Path] = None
        self._find_git_dir()
    
    def _find_git_dir(self):
        """Znajduje katalog .git"""
        current = self.working_dir
        while current != current.parent:
            if (current / ".git").is_dir():
                self._git_dir = current / ".git"
                self.working_dir = current
                break
            current = current.parent
    
    def is_repo(self) -> bool:
        """Sprawdza czy jesteśmy w repozytorium Git"""
        return self._git_dir is not None
    
    def _run_git(self, *args: str) -> GitResult:
        """Wykonuje polecenie git"""
        cmd = ["git"] + list(args)
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.working_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            return GitResult(
                success=result.returncode == 0,
                output=result.stdout.strip(),
                error=result.stderr.strip(),
                operation=" ".join(args)
            )
        except subprocess.TimeoutExpired:
            return GitResult(
                success=False,
                output="",
                error="Timeout",
                operation=" ".join(args)
            )
        except Exception as e:
            return GitResult(
                success=False,
                output="",
                error=str(e),
                operation=" ".join(args)
            )
    
    def get_status(self) -> Optional[GitStatus]:
        """Pobiera status repozytorium"""
        if not self.is_repo():
            return None
        
        # Pobierz gałąź
        branch_result = self._run_git("branch", "--show-current")
        branch = branch_result.output if branch_result.success else "unknown"
        
        # Pobierz status
        status_result = self._run_git("status", "--porcelain", "-b")
        if not status_result.success:
            return None
        
        staged = []
        modified = []
        untracked = []
        ahead = behind = 0
        
        for line in status_result.output.split('\n'):
            if line.startswith('##'):
                # Parsuj ahead/behind
                if 'ahead' in line:
                    match = re.search(r'ahead (\d+)', line)
                    if match:
                        ahead = int(match.group(1))
                if 'behind' in line:
                    match = re.search(r'behind (\d+)', line)
                    if match:
                        behind = int(match.group(1))
            elif len(line) >= 3:
                status_code = line[:2]
                filename = line[3:]
                
                if status_code[0] in 'MADRC':
                    staged.append(filename)
                if status_code[1] == 'M':
                    modified.append(filename)
                if status_code == '??':
                    untracked.append(filename)
        
        return GitStatus(
            branch=branch,
            is_clean=len(staged) == 0 and len(modified) == 0,
            staged=staged,
            modified=modified,
            untracked=untracked,
            ahead=ahead,
            behind=behind
        )
    
    def get_branches(self, remote: bool = False) -> List[str]:
        """Pobiera listę gałęzi"""
        if remote:
            result = self._run_git("branch", "-r")
        else:
            result = self._run_git("branch")
        
        if not result.success:
            return []
        
        branches = []
        for line in result.output.split('\n'):
            branch = line.strip().lstrip('* ')
            if branch and not branch.startswith('HEAD'):
                branches.append(branch)
        
        return branches
    
    def get_log(self, n: int = 10) -> List[GitCommit]:
        """Pobiera historię commitów"""
        result = self._run_git(
            "log",
            f"-{n}",
            "--pretty=format:%H|%h|%s|%an|%ad",
            "--date=short"
        )
        
        if not result.success:
            return []
        
        commits = []
        for line in result.output.split('\n'):
            if '|' in line:
                parts = line.split('|', 4)
                if len(parts) >= 5:
                    commits.append(GitCommit(
                        hash=parts[0],
                        short_hash=parts[1],
                        message=parts[2],
                        author=parts[3],
                        date=parts[4]
                    ))
        
        return commits
    
    def add(self, *paths: str) -> GitResult:
        """Dodaje pliki do staged"""
        if not paths:
            return self._run_git("add", "-A")
        return self._run_git("add", *paths)
    
    def commit(self, message: str, add_all: bool = False) -> GitResult:
        """Tworzy commit"""
        if add_all:
            return self._run_git("commit", "-am", message)
        return self._run_git("commit", "-m", message)
    
    def push(self, remote: str = "origin", branch: Optional[str] = None) -> GitResult:
        """Wypycha zmiany"""
        if branch:
            return self._run_git("push", remote, branch)
        return self._run_git("push")
    
    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> GitResult:
        """Pobiera zmiany"""
        if branch:
            return self._run_git("pull", remote, branch)
        return self._run_git("pull")
    
    def checkout(self, target: str, create: bool = False) -> GitResult:
        """Przełącza gałąź"""
        if create:
            return self._run_git("checkout", "-b", target)
        return self._run_git("checkout", target)
    
    def stash(self, pop: bool = False) -> GitResult:
        """Operacje stash"""
        if pop:
            return self._run_git("stash", "pop")
        return self._run_git("stash")
    
    def execute_natural(self, natural_command: str) -> GitResult:
        """Wykonuje naturalne polecenie Git"""
        natural_lower = natural_command.lower().strip()
        
        # Sprawdź proste mapowania
        for key, cmd in self.NATURAL_COMMANDS.items():
            if natural_lower == key or natural_lower.startswith(key + " "):
                args = cmd.replace("git ", "").split()
                rest = natural_lower.replace(key, "").strip()
                if rest:
                    args.append(rest)
                return self._run_git(*args)
        
        # Parsuj złożone polecenia
        patterns = [
            (r"zatwierdź z komentarzem (.+)", lambda m: self.commit(m.group(1))),
            (r"commit (.+)", lambda m: self.commit(m.group(1))),
            (r"przełącz na (.+)", lambda m: self.checkout(m.group(1))),
            (r"checkout (.+)", lambda m: self.checkout(m.group(1))),
            (r"utwórz gałąź (.+)", lambda m: self.checkout(m.group(1), create=True)),
            (r"dodaj (.+)", lambda m: self.add(m.group(1))),
        ]
        
        for pattern, handler in patterns:
            match = re.match(pattern, natural_lower)
            if match:
                return handler(match)
        
        # Fallback - spróbuj wykonać jako surowe polecenie git
        if natural_lower.startswith("git "):
            args = natural_lower.replace("git ", "").split()
            return self._run_git(*args)
        
        return GitResult(
            success=False,
            output="",
            error=f"Nie rozpoznano polecenia: {natural_command}",
            operation="parse"
        )
    
    def get_suggestions(self, partial: str = "") -> List[Tuple[str, str]]:
        """Generuje sugestie"""
        suggestions = []
        status = self.get_status()
        
        if status:
            # Sugestie kontekstowe
            if status.modified or status.untracked:
                suggestions.append(("dodaj wszystko", "git add -A"))
            if status.staged:
                suggestions.append(("zatwierdź", "git commit"))
            if status.ahead > 0:
                suggestions.append(("wypchnij", f"git push ({status.ahead} ahead)"))
            if status.behind > 0:
                suggestions.append(("pobierz", f"git pull ({status.behind} behind)"))
        
        # Ogólne sugestie
        for natural, bash in self.NATURAL_COMMANDS.items():
            if not partial or partial.lower() in natural.lower():
                suggestions.append((natural, bash))
        
        return suggestions[:10]
    
    def format_status_for_voice(self) -> str:
        """Formatuje status do odczytu głosowego"""
        status = self.get_status()
        if not status:
            return "To nie jest repozytorium Git."
        
        parts = [f"Gałąź {status.branch}."]
        
        if status.is_clean:
            parts.append("Katalog roboczy jest czysty.")
        else:
            if status.staged:
                parts.append(f"{len(status.staged)} plików do zatwierdzenia.")
            if status.modified:
                parts.append(f"{len(status.modified)} zmodyfikowanych.")
            if status.untracked:
                parts.append(f"{len(status.untracked)} nieśledzonych.")
        
        if status.ahead:
            parts.append(f"{status.ahead} commitów do wypchnięcia.")
        if status.behind:
            parts.append(f"{status.behind} commitów do pobrania.")
        
        return " ".join(parts)
    
    def format_status_for_display(self) -> str:
        """Formatuje status do wyświetlenia"""
        status = self.get_status()
        if not status:
            return "Nie jesteś w repozytorium Git."
        
        lines = [
            f"┌─ Git: {status.branch} ─────────────────────",
        ]
        
        if status.ahead or status.behind:
            lines.append(f"│ ↑{status.ahead} ↓{status.behind}")
        
        if status.staged:
            lines.append(f"│ Staged: {', '.join(status.staged[:3])}")
        if status.modified:
            lines.append(f"│ Modified: {', '.join(status.modified[:3])}")
        if status.untracked:
            lines.append(f"│ Untracked: {', '.join(status.untracked[:3])}")
        
        if status.is_clean:
            lines.append("│ ✓ Czysty katalog roboczy")
        
        lines.append("└──────────────────────────────────────")
        return "\n".join(lines)
