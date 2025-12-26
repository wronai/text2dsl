# Tryb głosowy

## Uruchomienie

```bash
text2dsl --voice --lang pl
```

## Debug

```bash
text2dsl --voice --lang pl --verbose
```

W trybie `--verbose` zobaczysz logi warstwy głosowej (`[text2dsl][voice][debug] ...`).

## Zależności

Warstwa głosowa może wymagać dodatkowych zależności systemowych (np. `portaudio`, `libstdc++`).

Jeśli STT nie może wystartować, aplikacja nie będzie wisieć w pętli — zakończy sesję głosową i wypisze czytelny komunikat.
