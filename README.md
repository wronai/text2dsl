# text2dsl 🎤

**Głosowa nawigacja CLI z kontekstowym wsparciem**

[![PyPI](https://img.shields.io/pypi/v/text2dsl)](https://pypi.org/project/text2dsl/)
[![Python](https://img.shields.io/pypi/pyversions/text2dsl)](https://pypi.org/project/text2dsl/)
[![License](https://img.shields.io/pypi/l/text2dsl)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/text2dsl)](https://pypi.org/project/text2dsl/)
[![GitHub stars](https://img.shields.io/github/stars/wronai/text2dsl?style=social)](https://github.com/wronai/text2dsl/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/wronai/text2dsl?style=social)](https://github.com/wronai/text2dsl/network/members)
[![GitHub issues](https://img.shields.io/github/issues/wronai/text2dsl)](https://github.com/wronai/text2dsl/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/wronai/text2dsl)](https://github.com/wronai/text2dsl/pulls)
[![Tests](https://img.shields.io/github/actions/workflow/status/wronai/text2dsl/test.yml?label=tests)](https://github.com/wronai/text2dsl/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue.svg)](http://mypy-lang.org/)
[![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20windows-lightgrey)](https://github.com/wronai/text2dsl)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue)](https://pypi.org/project/text2dsl/)
[![Dependencies](https://img.shields.io/badge/dependencies-azure%20%7C%20openai-blue)](https://github.com/wronai/text2dsl)
[![Languages](https://img.shields.io/badge/languages-pl%20%7C%20de%20%7C%20en-blue)](https://github.com/wronai/text2dsl)

Framework do głosowej i tekstowej interakcji z narzędziami deweloperskimi (make, shell, git, docker, python) poprzez warstwę DSL z inteligentnymi sugestiami.

## 🌍 Obsługiwane języki

| Język | Kod | TTS Voice | Przykład |
|-------|-----|-----------|----------|
| 🇵🇱 Polski | `pl` | pl-PL-MarekNeural | "zbuduj projekt" |
| 🇩🇪 Deutsch | `de` | de-DE-ConradNeural | "bauen Projekt" |
| 🇬🇧 English | `en` | en-US-GuyNeural | "build project" |

## 🏗 Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    Użytkownik                               │
│              (głos / tekst / terminal)                      │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│              Voice Layer (TTS/STT)                          │
│         Whisper / Edge-TTS / pyttsx3                        │
│              🇵🇱 PL  |  🇩🇪 DE  |  🇬🇧 EN                      │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                 text2DSL Parser                             │
│     Wielojęzyczne rozpoznawanie intencji + kontekst         │
└────────────────────────────┬────────────────────────────────┘
                             │
    ┌───────────┬────────────┼───────────┬─────────────┐
    │           │            │           │             │
┌───▼───┐  ┌────▼────┐  ┌────▼───┐  ┌────▼─────┐  ┌────▼─────┐
│ text2 │  │ text2   │  │ text2  │  │  text2   │  │  text2   │
│ make  │  │ shell   │  │ git    │  │  docker  │  │  python  │
└───────┘  └─────────┘  └────────┘  └──────────┘  └──────────┘
```

## 🚀 Instalacja

```bash
# Podstawowa instalacja
pip install -e .

# Z obsługą głosu
pip install -e ".[voice]"

# Pełna instalacja (voice + dev tools)
pip install -e ".[all]"
```

## 📖 Użycie

### Tryb interaktywny

```bash
# Polski (domyślny)
text2dsl

# Niemiecki
text2dsl --lang de

# Angielski  
text2dsl --lang en
```

### Pojedyncze polecenie

```bash
# Polski
text2dsl "zbuduj projekt"
text2dsl "uruchom testy"
text2dsl "wypchnij zmiany"

# Niemiecki
text2dsl --lang de "bauen"
text2dsl --lang de "Tests ausführen"

# Angielski
text2dsl --lang en "build project"
text2dsl --lang en "run tests"
```

### Tryb głosowy

```bash
# Głosowy tryb w polskim
text2dsl --voice --lang pl

# Głosowy tryb w niemieckim
text2dsl --voice --lang de

# Głosowy tryb w angielskim
text2dsl --voice --lang en
```

### Eksport projektu

```bash
# Eksport do ZIP
text2dsl --export

# Eksport do TAR.GZ
text2dsl --export --format tar.gz

# Eksport z własną nazwą
text2dsl --export -o moj_projekt.zip

# Lista plików w projekcie
text2dsl --list-files
```

### W kodzie Python

```python
from text2dsl import (
    Text2DSLOrchestrator, 
    OrchestratorConfig,
    VoiceConfig,
    get_language_config
)

# Konfiguracja dla języka niemieckiego
lang_config = get_language_config("de")
voice_config = VoiceConfig(
    language="de",
    voice_name=lang_config.edge_tts_voice
)

config = OrchestratorConfig(
    voice_enabled=True,
    voice_config=voice_config,
    language="de"
)

orchestrator = Text2DSLOrchestrator(config)

# Wykonaj polecenie po niemiecku
response = orchestrator.process("bauen")  # → make build
print(response.message)

# Zmień język na polski
orchestrator.parser.set_language("pl")
response = orchestrator.process("zbuduj")  # → make build
```

## 🗣 Przykłady poleceń w różnych językach

### Make

| Polski | Deutsch | English | Komenda |
|--------|---------|---------|---------|
| zbuduj | bauen | build | `make all` |
| testy | tests | tests | `make test` |
| wyczyść | säubern | clean | `make clean` |
| zainstaluj | installieren | install | `make install` |

### Git

| Polski | Deutsch | English | Komenda |
|--------|---------|---------|---------|
| status | status | status | `git status` |
| zatwierdź | bestätigen | commit | `git commit` |
| wypchnij | hochladen | push | `git push` |
| pobierz | herunterladen | pull | `git pull` |
| gałąź | zweig | branch | `git branch` |

### Docker

| Polski | Deutsch | English | Komenda |
|--------|---------|---------|---------|
| kontenery | container | containers | `docker ps` |
| zbuduj obraz | image bauen | build image | `docker build` |
| uruchom serwisy | services starten | start services | `compose up` |

### Kontekstowe

| Polski | Deutsch | English | Akcja |
|--------|---------|---------|-------|
| dalej | weiter | next | następna sugestia |
| powtórz | wiederholen | repeat | powtórz komendę |
| cofnij | zurück | back | cofnij |
| tak | ja | yes | potwierdź |
| nie | nein | no | anuluj |

## 📦 Eksport i pobieranie

```python
from text2dsl import ArchiveManager

# Utwórz menedżera archiwum
manager = ArchiveManager("/path/to/project")

# Eksportuj do ZIP
result = manager.export_zip("backup.zip")
print(f"Utworzono: {result.path}")
print(f"Plików: {result.files_count}")
print(f"Rozmiar: {manager.format_size(result.size_bytes)}")

# Eksportuj do TAR.GZ
result = manager.export_tar("backup.tar.gz", compression="gz")

# Eksportuj wybrane pliki
result = manager.export_files(
    files=["src/", "Makefile", "README.md"],
    output_path="partial.zip"
)

# Lista plików
files = manager.list_files()
for f in files:
    print(f)
```

## 🔧 Konfiguracja głosu

```python
from text2dsl import VoiceConfig, VoiceBackend, VoiceLayer

# Pełna konfiguracja
config = VoiceConfig(
    stt_backend=VoiceBackend.WHISPER,    # STT: Whisper
    tts_backend=VoiceBackend.EDGE_TTS,   # TTS: Microsoft Edge
    language="pl",                        # Język
    auto_detect_language=True,           # Automatyczne wykrywanie
    speech_rate=150,                      # Szybkość mowy
    volume=1.0,                           # Głośność
)

voice = VoiceLayer(config)

# Mów po polsku
voice.speak("Witaj!")

# Zmień na niemiecki
voice.set_language("de", gender="female")
voice.speak("Willkommen!")

# Zmień na angielski
voice.set_language("en", gender="male")
voice.speak("Welcome!")

# Pobierz komunikat systemowy
msg = voice.get_message("listening")  # → "Słucham..." / "Ich höre..." / "Listening..."
```

## 📁 Struktura projektu

```
text2dsl/
├── text2dsl/
│   ├── __init__.py
│   ├── __main__.py              # CLI
│   ├── orchestrator.py          # Główny koordynator
│   ├── core/
│   │   ├── dsl_parser.py        # Parser wielojęzyczny
│   │   ├── context_manager.py   # Zarządzanie kontekstem
│   │   └── suggestion_engine.py # Silnik sugestii
│   ├── layers/
│   │   ├── voice_layer.py       # TTS/STT (PL/DE/EN)
│   │   ├── text2make.py
│   │   ├── text2shell.py
│   │   ├── text2git.py
│   │   ├── text2docker.py
│   │   └── text2python.py
│   └── utils/
│       └── archive.py           # Eksport/archiwizacja
├── tests/
├── examples/
├── pyproject.toml
├── Makefile
└── README.md
```

## 🧪 Testy

```bash
# Uruchom testy
make test

# Z pokryciem
make test-cov

# Lint
make lint

# Formatowanie
make format
```

## 📄 Licencja

Apache 2

## 👤 Autor

Softreck - [softreck.dev](https://softreck.dev)
