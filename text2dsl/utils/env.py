import os
from pathlib import Path
from typing import Optional, Union


def load_env_file(path: Union[str, Path], override: bool = False) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False

    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[len("export ") :].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
            value = value[1:-1]

        if not override and key in os.environ:
            continue

        os.environ[key] = value

    return True


def get_env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    v_norm = v.strip().lower()
    if v_norm in {"1", "true", "yes", "y", "on"}:
        return True
    if v_norm in {"0", "false", "no", "n", "off"}:
        return False
    return default


def get_env_str(key: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(key)
    return v if v is not None else default
