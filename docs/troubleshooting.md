# Rozwiązywanie problemów

## Tryb głosowy: GLIBCXX / conda

Jeśli widzisz błąd w stylu:

- `GLIBCXX_3.4.xx not found`
- konflikt `libstdc++` pomiędzy systemem a conda

to jest to problem środowiskowy (ładowanie bibliotek C). Najczęstsze rozwiązania:

1. Uruchom w czystym venv bez aktywnego `conda base`.
2. Zaktualizuj `libstdc++` w środowisku conda.
3. Upewnij się, że system ma potrzebne biblioteki audio.

Uruchom z `--verbose`, żeby zobaczyć dokładnie, na którym kroku pipeline głosowy się zatrzymuje.

## Pytest: błędy pluginów

Jeśli testy wywalają się przez zewnętrzne pluginy pytest, uruchamiaj:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v
```
