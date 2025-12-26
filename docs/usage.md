# Użycie

## Tryb interaktywny

```bash
text2dsl
```

## Pojedyncze polecenie

```bash
text2dsl "zbuduj projekt"
text2dsl "uruchom testy"
text2dsl "wypchnij zmiany"
```

## Verbose (pełne logowanie krok po kroku)

```bash
text2dsl --verbose "uruchom testy"
text2dsl --verbose "wypchnij zmiany"
```

W `--verbose` zobaczysz m.in.:

- `parsed` (wynik parsera)
- `route` (routing do warstwy)
- `exec.*` (co jest wykonywane)

## Tryb głosowy

```bash
text2dsl --voice --lang pl
```

Jeśli uruchamiasz tryb głosowy z debug:

```bash
text2dsl --voice --lang pl --verbose
```

## Makefile

- `make run` uruchamia tryb interaktywny
- `make voice` uruchamia tryb głosowy
- `make stop` kończy działanie (bezpieczny no-op, gdy nic nie działa w tle)
