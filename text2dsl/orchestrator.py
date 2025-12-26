"""
Text2DSL Orchestrator - Główny koordynator warstw

Łączy wszystkie komponenty:
1. Voice Layer (TTS/STT)
2. DSL Parser
3. Context Manager
4. Suggestion Engine
5. Execution Layers (Make, Shell, Git, Docker, Python)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Union
from pathlib import Path
import threading
import queue
import time

from .core import (
    DSLParser,
    ParsedCommand,
    CommandType,
    ContextManager,
    ExecutionResult,
    SuggestionEngine,
    Suggestion,
)
from .layers import (
    VoiceLayer,
    VoiceConfig,
    MockVoiceLayer,
    Text2Make,
    Text2Shell,
    Text2Git,
    Text2Docker,
    Text2Python,
)


@dataclass
class OrchestratorConfig:
    """Konfiguracja orchestratora"""

    working_dir: Optional[str] = None
    voice_enabled: bool = True
    voice_config: Optional[VoiceConfig] = None
    auto_confirm: bool = False  # Automatycznie potwierdza akcje
    verbose: bool = True
    quiet: bool = False
    language: str = "pl"


@dataclass
class ExecutionResponse:
    """Odpowiedź na wykonanie polecenia"""

    success: bool
    message: str
    result: Optional[Any] = None
    suggestions: List[Suggestion] = field(default_factory=list)
    needs_confirmation: bool = False
    confirmation_prompt: Optional[str] = None


class Text2DSLOrchestrator:
    """
    Główny orchestrator text2dsl

    Koordynuje przepływ:
    1. Wejście głosowe/tekstowe
    2. Parsowanie DSL
    3. Routing do odpowiedniej warstwy
    4. Wykonanie
    5. Odpowiedź głosowa/tekstowa

    Użycie:
        orchestrator = Text2DSLOrchestrator()

        # Tryb tekstowy
        response = orchestrator.process("zbuduj projekt")

        # Tryb głosowy
        orchestrator.start_voice_session()
    """

    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig()

        # Core components
        self.parser = DSLParser()
        self.context = ContextManager(self.config.working_dir)
        self.suggestions = SuggestionEngine()

        # Execution layers
        self.make = Text2Make(self.context.working_dir)
        self.shell = Text2Shell(self.context.working_dir)
        self.git = Text2Git(self.context.working_dir)
        self.docker = Text2Docker(self.context.working_dir)
        self.python = Text2Python(self.context.working_dir)

        # Voice layer
        self.voice: Optional[VoiceLayer] = None
        if self.config.voice_enabled:
            try:
                voice_config = self.config.voice_config or VoiceConfig()
                self.voice = VoiceLayer(voice_config)
            except Exception as e:
                print(f"Voice disabled: {e}")

        # State
        self._running = False
        self._command_queue: queue.Queue = queue.Queue()

        # Callbacks
        self._on_response: Optional[Callable[[ExecutionResponse], None]] = None
        self._on_suggestion: Optional[Callable[[List[Suggestion]], None]] = None

    def process(self, input_text: str) -> ExecutionResponse:
        """
        Przetwarza polecenie tekstowe

        Args:
            input_text: Polecenie (naturalne lub DSL)

        Returns:
            ExecutionResponse z wynikiem
        """
        # Parsuj polecenie
        command = self.parser.parse(input_text)

        self._debug(
            "parsed",
            {
                "input": input_text,
                "type": command.type.name,
                "action": command.action,
                "target": command.target,
                "args": command.args,
                "confidence": command.confidence,
                "lang": getattr(command, "detected_language", None),
            },
        )

        # Obsłuż komendy kontekstowe
        if command.type == CommandType.CONTEXT:
            self._debug("route", {"to": "context", "action": command.action})
            return self._handle_context_command(command)

        # Obsłuż zapytania
        if command.type == CommandType.QUERY:
            self._debug("route", {"to": "query", "action": command.action})
            return self._handle_query(command)

        # Routuj do odpowiedniej warstwy
        self._debug("route", {"to": command.type.name})
        response = self._route_and_execute(command)

        # Aktualizuj kontekst
        self.context.update_state(command.type.name, command.target)
        self.suggestions.record_command(input_text)

        # Generuj sugestie
        response.suggestions = self.suggestions.get_suggestions(context=self.context.to_dict())

        return response

    def _debug(self, event: str, data: Optional[Dict[str, Any]] = None):
        if not self.config.verbose:
            return
        payload = "" if not data else f" {data}"
        print(f"[text2dsl][debug] {event}{payload}")

    def _preview_text(self, text: Optional[str], limit: int = 500) -> str:
        if not text:
            return ""
        t = text.strip("\n")
        if len(t) <= limit:
            return t
        return t[:limit] + "..."

    def _with_trace(self, message: str, command: ParsedCommand, exec_cmd: str, result: Any) -> str:
        limit = 800 if self.config.verbose else 200

        lines: List[str] = [message, ""]
        lines.append(
            "TRACE: "
            f"DSL={command.type.name} action={command.action} target={command.target} "
            f"args={command.args} confidence={command.confidence:.2f}"
        )
        lines.append(f"TRACE: ROUTE={command.type.name}")
        lines.append(f"TRACE: EXEC={exec_cmd}")

        success = getattr(result, "success", None)
        if success is not None:
            lines.append(f"TRACE: SUCCESS={success}")

        return_code = getattr(result, "return_code", None)
        if return_code is not None:
            lines.append(f"TRACE: EXIT={return_code}")

        out_preview = self._preview_text(getattr(result, "output", ""), limit=limit)
        err_preview = self._preview_text(getattr(result, "error", ""), limit=limit)
        if out_preview:
            lines.append("TRACE: STDOUT:")
            lines.append(out_preview)
        if err_preview:
            lines.append("TRACE: STDERR:")
            lines.append(err_preview)

        return "\n".join(lines)

    def _handle_context_command(self, command: ParsedCommand) -> ExecutionResponse:
        """Obsługuje komendy kontekstowe (dalej, cofnij, powtórz)"""
        action = command.action

        if action == "confirm":
            pending = self.context.get_pending_confirmation()
            if pending:
                # Wykonaj oczekującą akcję
                self.context.clear_pending_confirmation()
                return self.process(pending["details"].get("command", ""))
            return ExecutionResponse(
                success=True, message="Nie ma oczekującej akcji do potwierdzenia."
            )

        if action == "deny" or action == "cancel":
            self.context.clear_pending_confirmation()
            return ExecutionResponse(success=True, message="Anulowano.")

        if action == "next":
            next_cmd = self.suggestions.get_next_likely_command()
            if next_cmd:
                return ExecutionResponse(
                    success=True,
                    message=f"Sugeruję: {next_cmd}",
                    needs_confirmation=True,
                    confirmation_prompt=f"Czy wykonać '{next_cmd}'?",
                )
            return ExecutionResponse(success=True, message="Brak sugestii następnego kroku.")

        if action == "undo":
            return ExecutionResponse(
                success=False, message="Cofanie nie jest jeszcze zaimplementowane."
            )

        if action == "repeat":
            if command.raw_input and command.type != CommandType.CONTEXT:
                return self.process(command.raw_input)
            return ExecutionResponse(
                success=False, message="Brak poprzedniej komendy do powtórzenia."
            )

        return ExecutionResponse(success=False, message=f"Nieznana komenda kontekstowa: {action}")

    def _handle_query(self, command: ParsedCommand) -> ExecutionResponse:
        """Obsługuje zapytania (co mogę zrobić?, status)"""
        action = command.action

        if action == "options":
            options = self.context.get_contextual_options()
            message_parts = ["Dostępne opcje:"]
            for category, opts in options.items():
                message_parts.append(f"\n{category}:")
                for opt in opts[:5]:
                    message_parts.append(f"  - {opt}")

            return ExecutionResponse(
                success=True,
                message="\n".join(message_parts),
                suggestions=self.suggestions.get_suggestions(context=self.context.to_dict()),
            )

        if action == "status":
            status_parts = []

            # Status projektu
            if self.context.project:
                status_parts.append(f"Projekt: {self.context.project.name}")
                if self.context.project.has_makefile:
                    status_parts.append(
                        f"Makefile: {len(self.context.project.makefile_targets)} celów"
                    )
                if self.context.project.has_git:
                    git_status = self.git.get_status()
                    if git_status:
                        status_parts.append(f"Git: {git_status.branch}")
                if self.context.project.has_docker_compose:
                    status_parts.append("Docker Compose: dostępny")

            return ExecutionResponse(
                success=True,
                message="\n".join(status_parts) if status_parts else "Brak aktywnego projektu.",
            )

        if action == "help":
            help_text = """
Dostępne polecenia:
  Ogólne: status, opcje, pomoc
  Make: zbuduj, testy, wyczyść, [cel]
  Shell: pokaż pliki, uruchom [cmd]
  Git: status, commit, push, pull
  Docker: kontenery, compose up/down
  Python: testy, zainstaluj [pkg]
  
Kontekstowe: dalej, cofnij, powtórz, tak, nie
"""
            return ExecutionResponse(success=True, message=help_text.strip())

        return ExecutionResponse(success=True, message="Jak mogę pomóc?")

    def _route_and_execute(self, command: ParsedCommand) -> ExecutionResponse:
        """Routuje komendę do odpowiedniej warstwy i wykonuje"""

        if command.type == CommandType.MAKE:
            return self._execute_make(command)

        if command.type == CommandType.SHELL:
            return self._execute_shell(command)

        if command.type == CommandType.GIT:
            return self._execute_git(command)

        if command.type == CommandType.DOCKER:
            return self._execute_docker(command)

        if command.type == CommandType.PYTHON:
            return self._execute_python(command)

        # Fallback - spróbuj shell
        return self._execute_shell(command)

    def _execute_make(self, command: ParsedCommand) -> ExecutionResponse:
        """Wykonuje polecenie Make"""
        if not self.make.has_makefile():
            return ExecutionResponse(success=False, message="Brak Makefile w bieżącym katalogu.")

        # Rozwiąż naturalną komendę na cel
        raw = (command.raw_input or "").strip()
        raw_lower = raw.lower()
        target = command.target

        if raw_lower.startswith("make"):
            parts = raw.split()
            if len(parts) >= 2:
                target = parts[1]
        elif command.action and command.action != "inferred":
            target = self.make.resolve_natural_command(command.action)

        if target is None and command.args:
            target = self.make.resolve_natural_command(command.args[0])

        self._debug("exec.make", {"target": target})

        # Wykonaj
        result = self.make.run(target)

        self._debug(
            "exec.make.result",
            {"success": result.success, "return_code": result.return_code, "target": result.target},
        )

        self.context.add_execution_result(
            ExecutionResult(
                success=result.success,
                output=result.output,
                error=result.error,
                return_code=result.return_code,
                command=f"make {target or 'default'}",
            )
        )

        if result.success:
            message = f"Make {target or 'default'}: sukces ({result.duration_ms}ms)"
        else:
            message = f"Make {target or 'default'}: błąd\n{result.error[:200]}"

        exec_cmd = f"make {target}".strip() if target else "make"
        message = self._with_trace(message, command, exec_cmd, result)

        return ExecutionResponse(success=result.success, message=message, result=result)

    def _execute_shell(self, command: ParsedCommand) -> ExecutionResponse:
        """Wykonuje polecenie Shell"""
        # Zbierz komendę
        if command.action == "run" and command.target:
            shell_cmd = command.target
        elif command.args:
            shell_cmd = " ".join(command.args)
        else:
            shell_cmd = self.shell.translate_to_bash(command.raw_input)

        self._debug("exec.shell", {"command": shell_cmd})

        result = self.shell.run(shell_cmd)

        self._debug(
            "exec.shell.result",
            {
                "success": result.success,
                "return_code": result.return_code,
                "command": result.command,
            },
        )

        self.context.add_execution_result(
            ExecutionResult(
                success=result.success,
                output=result.output,
                error=result.error,
                return_code=result.return_code,
                command=shell_cmd,
            )
        )

        if result.success:
            output_preview = result.output[:500] if result.output else "OK"
            message = output_preview
        else:
            message = f"Błąd: {result.error[:200]}"

        message = self._with_trace(message, command, shell_cmd, result)

        return ExecutionResponse(success=result.success, message=message, result=result)

    def _execute_git(self, command: ParsedCommand) -> ExecutionResponse:
        """Wykonuje polecenie Git"""
        if not self.git.is_repo():
            return ExecutionResponse(success=False, message="Nie jesteś w repozytorium Git.")

        # Użyj naturalnego wykonania
        natural_cmd = command.raw_input
        if command.action == "status":
            natural_cmd = "status"
        elif command.action == "commit" and command.target:
            natural_cmd = f"commit {command.target}"

        self._debug("exec.git", {"natural": natural_cmd})
        result = self.git.execute_natural(natural_cmd)

        self._debug(
            "exec.git.result",
            {"success": result.success, "operation": result.operation, "error": result.error[:200]},
        )

        if result.success:
            message = result.output[:500] if result.output else "OK"
        else:
            message = f"Błąd: {result.error[:200]}"

        exec_cmd = f"git {result.operation}".strip()
        message = self._with_trace(message, command, exec_cmd, result)

        return ExecutionResponse(success=result.success, message=message, result=result)

    def _execute_docker(self, command: ParsedCommand) -> ExecutionResponse:
        """Wykonuje polecenie Docker"""
        if not self.docker.has_docker():
            return ExecutionResponse(
                success=False, message="Docker nie jest zainstalowany lub niedostępny."
            )

        self._debug("exec.docker", {"natural": command.raw_input})
        result = self.docker.execute_natural(command.raw_input)

        self._debug(
            "exec.docker.result",
            {"success": result.success, "operation": result.operation, "error": result.error[:200]},
        )

        if result.success:
            message = result.output[:500] if result.output else "OK"
        else:
            message = f"Błąd: {result.error[:200]}"

        exec_cmd = f"docker {result.operation}".strip()
        message = self._with_trace(message, command, exec_cmd, result)

        return ExecutionResponse(success=result.success, message=message, result=result)

    def _execute_python(self, command: ParsedCommand) -> ExecutionResponse:
        """Wykonuje polecenie Python"""
        self._debug("exec.python", {"natural": command.raw_input})
        result = self.python.execute_natural(command.raw_input)

        self._debug(
            "exec.python.result",
            {"success": result.success, "operation": result.operation, "error": result.error[:200]},
        )

        if result.success:
            message = result.output[:500] if result.output else "OK"
        else:
            message = f"Błąd: {result.error[:200]}"

        exec_cmd = f"python {result.operation}".strip()
        message = self._with_trace(message, command, exec_cmd, result)

        return ExecutionResponse(success=result.success, message=message, result=result)

    # ==================== Voice Interface ====================

    def speak(self, text: str):
        """Wymawia tekst"""
        if self.voice:
            self.voice.speak(text)
        if not self.config.quiet:
            print(f"🔊 {text}")

    def listen(self, timeout: float = 5.0) -> Optional[str]:
        """Nasłuchuje mowy"""
        if self.voice:
            return self.voice.listen(timeout)
        return None

    def start_voice_session(self):
        """Rozpoczyna sesję głosową"""
        if not self.voice:
            print("Voice nie jest dostępny.")
            return

        self._debug("voice.session.start", {"lang": self.config.language})

        self._running = True
        self.speak("Witaj! Jak mogę pomóc?")

        def on_speech(text: str):
            if not self._running:
                return

            print(f"📢 {text}")
            response = self.process(text)

            if response.needs_confirmation:
                self.speak(response.confirmation_prompt or "Czy potwierdzasz?")
            else:
                self.speak(response.message)

            if response.suggestions and self.config.verbose:
                print("\n" + self.suggestions.format_suggestions_for_display(response.suggestions))

        try:
            self.voice.start_listening(on_speech)
        except Exception as e:
            self._debug("voice.session.error", {"error": str(e)})
            print(f"Błąd voice: {e}")
            self.stop_voice_session()
            return

        if not self.voice.is_listening:
            self._debug("voice.session.listen_failed")
            self._running = False
            return

        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_voice_session()

    def stop_voice_session(self):
        """Zatrzymuje sesję głosową"""
        self._debug("voice.session.stop")
        self._running = False
        if self.voice:
            self.voice.stop_listening()
        self.speak("Do widzenia!")

    # ==================== Interactive Mode ====================

    def _select_suggestion(
        self, user_input: str, suggestions: List[Suggestion]
    ) -> Optional[Suggestion]:
        cleaned = user_input.strip()
        if not cleaned:
            return None

        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1].strip()

        if cleaned.endswith("."):
            cleaned = cleaned[:-1].strip()

        if cleaned.isdigit():
            idx = int(cleaned)
            if 1 <= idx <= len(suggestions):
                return suggestions[idx - 1]

        cleaned_lower = cleaned.lower()
        for s in suggestions:
            if s.shortcut and cleaned_lower == s.shortcut.lower():
                return s
        return None

    def interactive(self):
        """Tryb interaktywny (tekstowy)"""
        print("=" * 50)
        print("  text2dsl - Głosowa nawigacja CLI")
        print("=" * 50)
        print(f"Katalog: {self.context.working_dir}")
        print("Wpisz 'pomoc' aby zobaczyć dostępne polecenia.")
        print("Wpisz 'wyjdź' aby zakończyć.")
        print("-" * 50)

        # Pokaż początkowe sugestie
        suggestions = self.suggestions.get_suggestions(context=self.context.to_dict())
        displayed_suggestions: List[Suggestion] = []
        if suggestions:
            displayed_suggestions = suggestions[:5]
            print(self.suggestions.format_suggestions_for_display(displayed_suggestions))

        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                selected = self._select_suggestion(user_input, displayed_suggestions)
                if selected:
                    user_input = selected.command

                if user_input.lower() in ["wyjdź", "exit", "quit", "q"]:
                    print("Do widzenia!")
                    break

                response = self.process(user_input)

                # Wyświetl odpowiedź
                print(f"\n{response.message}")

                # Wyświetl sugestie
                if response.suggestions:
                    displayed_suggestions = response.suggestions[:3]
                    print(self.suggestions.format_suggestions_for_display(displayed_suggestions))
                else:
                    displayed_suggestions = []

                # Obsłuż potwierdzenie
                if response.needs_confirmation:
                    confirm = input("(tak/nie) > ").strip().lower()
                    if confirm in ["tak", "yes", "y", "t"]:
                        self.process("tak")
                    else:
                        self.process("nie")

            except KeyboardInterrupt:
                print("\nDo widzenia!")
                break
            except Exception as e:
                print(f"Błąd: {e}")

    def change_directory(self, path: str) -> bool:
        """Zmienia katalog roboczy"""
        if self.context.change_directory(path):
            # Odśwież wszystkie warstwy
            self.make = Text2Make(self.context.working_dir)
            self.shell = Text2Shell(self.context.working_dir)
            self.git = Text2Git(self.context.working_dir)
            self.docker = Text2Docker(self.context.working_dir)
            self.python = Text2Python(self.context.working_dir)
            return True
        return False


# Aliasy dla wygody
Orchestrator = Text2DSLOrchestrator
