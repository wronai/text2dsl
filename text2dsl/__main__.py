#!/usr/bin/env python3
"""
text2dsl CLI - Interfejs wiersza poleceń

Użycie:
    text2dsl                        # Tryb interaktywny
    text2dsl "zbuduj projekt"       # Pojedyncze polecenie
    text2dsl --voice                # Tryb głosowy
    text2dsl --lang de              # Język niemiecki
    text2dsl --export               # Eksport projektu do ZIP
    text2dsl --status               # Status projektu
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="text2dsl - Głosowa nawigacja CLI (PL/DE/EN)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  text2dsl                          Tryb interaktywny (polski)
  text2dsl --lang en                Tryb interaktywny (angielski)
  text2dsl --lang de "bauen"        Wykonaj polecenie (niemiecki)
  text2dsl "zbuduj projekt"         Wykonaj polecenie (polski)
  text2dsl --voice --lang pl        Tryb głosowy (polski)
  text2dsl --export                 Eksport projektu do ZIP
  text2dsl --export --format tar.gz Eksport do TAR.GZ
  text2dsl -d /path/to/project      Ustaw katalog roboczy

Obsługiwane języki:
  pl - Polski (domyślny)
  de - Deutsch (niemiecki)
  en - English (angielski)
"""
    )
    
    parser.add_argument(
        "command",
        nargs="*",
        help="Polecenie do wykonania"
    )
    
    parser.add_argument(
        "-d", "--directory",
        help="Katalog roboczy",
        default=None
    )
    
    parser.add_argument(
        "-l", "--lang", "--language",
        choices=["pl", "de", "en"],
        default="pl",
        help="Język interfejsu (pl/de/en)"
    )
    
    parser.add_argument(
        "-v", "--voice",
        action="store_true",
        help="Włącz tryb głosowy"
    )
    
    parser.add_argument(
        "-s", "--status",
        action="store_true",
        help="Pokaż status projektu"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Ciche wyjście"
    )
    
    parser.add_argument(
        "--no-suggestions",
        action="store_true",
        help="Nie pokazuj sugestii"
    )
    
    parser.add_argument(
        "--export",
        action="store_true",
        help="Eksportuj projekt do archiwum"
    )
    
    parser.add_argument(
        "--format",
        choices=["zip", "tar", "tar.gz"],
        default="zip",
        help="Format archiwum (dla --export)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Ścieżka wyjściowa dla eksportu"
    )
    
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="Lista plików w projekcie"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="text2dsl 0.2.0"
    )
    
    args = parser.parse_args()
    
    # Import głównych komponentów
    from .orchestrator import Text2DSLOrchestrator, OrchestratorConfig
    from .layers.voice_layer import VoiceConfig, get_language_config
    from .utils.archive import ArchiveManager
    
    # Eksport projektu
    if args.export:
        source_dir = args.directory or "."
        manager = ArchiveManager(source_dir)
        
        if args.format == "zip":
            result = manager.export_zip(args.output)
        else:
            compression = "gz" if args.format == "tar.gz" else "none"
            result = manager.export_tar(args.output, compression)
        
        if result.success:
            print(f"✓ Eksport zakończony: {result.path}")
            print(f"  Plików: {result.files_count}")
            print(f"  Rozmiar: {manager.format_size(result.size_bytes)}")
        else:
            print(f"✗ Błąd eksportu: {result.error}")
            return 1
        return 0
    
    # Lista plików
    if args.list_files:
        source_dir = args.directory or "."
        manager = ArchiveManager(source_dir)
        files = manager.list_files()
        
        print(f"Pliki w projekcie ({len(files)}):")
        for f in files[:50]:
            print(f"  {f}")
        if len(files) > 50:
            print(f"  ... i {len(files) - 50} więcej")
        
        print(f"\nRozmiar: {manager.format_size(manager.get_project_size())}")
        return 0
    
    # Konfiguracja języka
    lang_config = get_language_config(args.lang)
    
    # Konfiguracja głosu
    voice_config = VoiceConfig(
        language=args.lang,
        voice_name=lang_config.edge_tts_voice,
    )
    
    # Konfiguracja orchestratora
    config = OrchestratorConfig(
        working_dir=args.directory,
        voice_enabled=args.voice,
        voice_config=voice_config,
        verbose=not args.quiet,
        language=args.lang
    )
    
    # Utwórz orchestrator
    orchestrator = Text2DSLOrchestrator(config)
    
    # Ustaw język parsera
    orchestrator.parser.set_language(args.lang)
    
    # Status
    if args.status:
        response = orchestrator.process("status")
        print(response.message)
        return 0
    
    # Pojedyncze polecenie
    if args.command:
        command_text = " ".join(args.command)
        response = orchestrator.process(command_text)
        
        print(response.message)
        
        if not args.no_suggestions and response.suggestions:
            # Wielojęzyczne etykiety
            labels = {
                "pl": "Sugestie",
                "de": "Vorschläge", 
                "en": "Suggestions"
            }
            print(f"\n{labels.get(args.lang, 'Suggestions')}:")
            for s in response.suggestions[:3]:
                print(f"  - {s.text}")
        
        return 0 if response.success else 1
    
    # Tryb głosowy
    if args.voice:
        try:
            # Powitanie w odpowiednim języku
            welcome = lang_config.messages.get("welcome", "Welcome!")
            if orchestrator.voice:
                orchestrator.voice.speak(welcome)
            else:
                print(welcome)
            
            orchestrator.start_voice_session()
        except KeyboardInterrupt:
            pass
        return 0
    
    # Tryb interaktywny
    try:
        orchestrator.interactive()
    except KeyboardInterrupt:
        pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
