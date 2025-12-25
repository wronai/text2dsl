#!/usr/bin/env python3
"""
Przykład użycia text2dsl

Demonstruje:
1. Podstawowe użycie orchestratora
2. Bezpośredni dostęp do warstw
3. Przetwarzanie naturalnych poleceń
4. Sugestie kontekstowe
"""

import os
import sys

# Dodaj ścieżkę do pakietu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def example_orchestrator():
    """Przykład użycia orchestratora"""
    print("=" * 50)
    print("Przykład 1: Orchestrator")
    print("=" * 50)
    
    from text2dsl import Text2DSLOrchestrator, OrchestratorConfig
    
    # Konfiguracja bez głosu (dla prostoty)
    config = OrchestratorConfig(
        voice_enabled=False,
        verbose=True
    )
    
    orchestrator = Text2DSLOrchestrator(config)
    
    # Przetwórz kilka poleceń
    commands = [
        "status",
        "opcje",
        "pokaż pliki"
    ]
    
    for cmd in commands:
        print(f"\n> {cmd}")
        response = orchestrator.process(cmd)
        print(response.message[:200])
        
        if response.suggestions:
            print("\nSugestie:")
            for s in response.suggestions[:3]:
                print(f"  - {s.text}")


def example_layers():
    """Przykład bezpośredniego użycia warstw"""
    print("\n" + "=" * 50)
    print("Przykład 2: Bezpośredni dostęp do warstw")
    print("=" * 50)
    
    from text2dsl.layers import Text2Shell, Text2Git, Text2Python
    
    # Shell
    print("\n--- Text2Shell ---")
    shell = Text2Shell()
    
    result = shell.run("echo 'Hello from text2dsl!'")
    print(f"Output: {result.output}")
    
    # Tłumaczenie naturalnego polecenia
    natural = "pokaż pliki"
    bash = shell.translate_to_bash(natural)
    print(f"'{natural}' → '{bash}'")
    
    # Git (jeśli jesteśmy w repo)
    print("\n--- Text2Git ---")
    git = Text2Git()
    
    if git.is_repo():
        status = git.get_status()
        print(f"Branch: {status.branch}")
        print(f"Clean: {status.is_clean}")
    else:
        print("Nie jesteś w repozytorium Git")
    
    # Python
    print("\n--- Text2Python ---")
    python = Text2Python()
    
    version = python.get_python_version()
    print(f"Python: {version}")
    
    if python.has_venv():
        print(f"Venv: aktywne")
    else:
        print("Venv: brak")


def example_parser():
    """Przykład użycia parsera DSL"""
    print("\n" + "=" * 50)
    print("Przykład 3: Parser DSL")
    print("=" * 50)
    
    from text2dsl.core import DSLParser, CommandType
    
    parser = DSLParser()
    
    # Lista poleceń do przetestowania
    commands = [
        "zbuduj",
        "uruchom testy",
        "status",
        "git push",
        "compose up",
        "zainstaluj requests",
        "dalej",
        "pomoc"
    ]
    
    for cmd in commands:
        result = parser.parse(cmd)
        print(f"'{cmd}' → {result.type.name}.{result.action} (pewność: {result.confidence:.0%})")


def example_context():
    """Przykład zarządzania kontekstem"""
    print("\n" + "=" * 50)
    print("Przykład 4: Context Manager")
    print("=" * 50)
    
    from text2dsl.core import ContextManager
    
    context = ContextManager()
    
    print(f"Katalog: {context.working_dir}")
    
    if context.project:
        print(f"Projekt: {context.project.name}")
        print(f"  Makefile: {'✓' if context.project.has_makefile else '✗'}")
        print(f"  Git: {'✓' if context.project.has_git else '✗'}")
        print(f"  Docker: {'✓' if context.project.has_dockerfile else '✗'}")
        print(f"  Python: {'✓' if context.project.has_python else '✗'}")
        
        if context.project.has_makefile:
            print(f"  Cele: {', '.join(context.project.makefile_targets[:5])}")
    
    # Opcje kontekstowe
    print("\nOpcje kontekstowe:")
    options = context.get_contextual_options()
    for category, opts in options.items():
        print(f"  {category}: {', '.join(opts[:3])}")


def example_suggestions():
    """Przykład silnika sugestii"""
    print("\n" + "=" * 50)
    print("Przykład 5: Silnik sugestii")
    print("=" * 50)
    
    from text2dsl.core import SuggestionEngine, ContextManager
    
    suggestions = SuggestionEngine()
    context = ContextManager()
    
    # Symuluj kilka komend
    suggestions.record_command("git status")
    suggestions.record_command("git add .")
    suggestions.record_command("git commit")
    
    # Pobierz sugestie
    sugs = suggestions.get_suggestions(
        context=context.to_dict()
    )
    
    print("Sugestie:")
    for s in sugs[:5]:
        print(f"  [{s.category}] {s.text} → {s.command}")
    
    # Przewiduj następną komendę
    next_cmd = suggestions.get_next_likely_command()
    if next_cmd:
        print(f"\nNastępna prawdopodobna komenda: {next_cmd}")


def main():
    """Uruchom wszystkie przykłady"""
    print("="*60)
    print("  text2dsl - Przykłady użycia")
    print("="*60)
    
    try:
        example_orchestrator()
    except Exception as e:
        print(f"Błąd w przykładzie orchestrator: {e}")
    
    try:
        example_layers()
    except Exception as e:
        print(f"Błąd w przykładzie layers: {e}")
    
    try:
        example_parser()
    except Exception as e:
        print(f"Błąd w przykładzie parser: {e}")
    
    try:
        example_context()
    except Exception as e:
        print(f"Błąd w przykładzie context: {e}")
    
    try:
        example_suggestions()
    except Exception as e:
        print(f"Błąd w przykładzie suggestions: {e}")
    
    print("\n" + "="*60)
    print("  Koniec przykładów")
    print("="*60)


if __name__ == "__main__":
    main()
