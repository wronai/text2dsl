# Instalacja

## Wymagania

- Python >= 3.9
- Make (opcjonalnie)

## Instalacja w trybie developerskim

```bash
pip install -e .
```

## Instalacja z zależnościami głosowymi

```bash
pip install -e ".[voice]"
```

## Pełna instalacja (voice + dev)

```bash
pip install -e ".[all]"
```

## Instalacja przez Makefile

```bash
make install
```

`make install` instaluje pakiet w trybie editable oraz (jeśli nie istnieje) tworzy `.env` na bazie `.env.example`.
