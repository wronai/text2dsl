# Konfiguracja (.env i zmienne środowiskowe)

## Pliki

- `.env` (lokalny, ignorowany przez git)
- `.env.example` (wzór do skopiowania)

Aplikacja wczytuje `.env` z katalogu roboczego (`-d/--directory` lub bieżący katalog).

## Obsługiwane zmienne

- `TEXT2DSL_LANG` lub `TEXT2DSL_LANGUAGE`:
  - `pl`, `de`, `en`
- `TEXT2DSL_VERBOSE`:
  - `1/true/yes/on` włącza logowanie debug
- `TEXT2DSL_QUIET`:
  - wycisza standardowe outputy (np. TTS `🔊`)
- `TEXT2DSL_NO_SUGGESTIONS`:
  - nie pokazuje sugestii w trybie pojedynczej komendy
- `TEXT2DSL_VOICE`:
  - wymusza tryb głosowy (gdy nie podano `--voice`)
- `TEXT2DSL_DIR` lub `TEXT2DSL_DIRECTORY`:
  - domyślny katalog roboczy, z którego wczytywany jest `.env`
- `WHISPER_MODEL`:
  - np. `base`, `small` (model Whisper)

## Priorytety

- jawne flagi CLI nadpisują `.env`
- `.env` nie nadpisuje już ustawionych zmiennych środowiskowych (chyba że w przyszłości dodasz override)
