# Dla developerów

## Testy

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest tests/ -v
```

## Formatowanie

```bash
make format
```

## Lint

```bash
make lint
```

## Build pakietu

```bash
make dist
```

## Publikacja

- `make publish-test` (TestPyPI)
- `make publish` (PyPI)

Wymaga skonfigurowanego uwierzytelnienia `twine`.
