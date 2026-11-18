"""Cargadores de datos: leen y validan los archivos JSON de assets/cfg."""

import json
import os
import re

CFG_DIR = "assets/cfg"
LEVELS_DIR = os.path.join(CFG_DIR, "levels")
LEVEL_FILE = re.compile(r"^level_(\d{2})\.json$")
ORIENTATIONS = ("horizontal", "vertical")
RESOURCE_SECTIONS = ("images", "sounds", "music", "fonts")


class ConfigError(ValueError):
    """Un archivo de configuración no existe, no es JSON válido o le faltan datos."""


def load_json(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"No existe el archivo de configuración: {path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"JSON inválido en {path}: {e}") from None


def require_keys(cfg: dict, keys: tuple[str, ...], source: str) -> None:
    """Lanza ConfigError si a `cfg` le falta alguna de las `keys`."""
    if not isinstance(cfg, dict):
        raise ConfigError(f"{source}: se esperaba un objeto JSON")
    missing = [k for k in keys if k not in cfg]
    if missing:
        raise ConfigError(f"{source}: faltan las claves {', '.join(missing)}")


def level_path(number: int) -> str:
    return os.path.join(LEVELS_DIR, f"level_{number:02d}.json")


def level_numbers() -> list[int]:
    """Números de los niveles que existen en assets/cfg/levels, de menor a mayor."""
    if not os.path.isdir(LEVELS_DIR):
        return []
    found = (LEVEL_FILE.match(name) for name in os.listdir(LEVELS_DIR))
    return sorted(int(m.group(1)) for m in found if m)


def load_level(number: int) -> dict:
    """Carga y valida el nivel `number` (1 = level_01.json)."""
    path = level_path(number)
    level = load_json(path)
    require_keys(level, ("round", "player_start", "bases"), path)
    require_keys(level["player_start"], ("x", "y"), f"{path} player_start")
    for i, base in enumerate(level["bases"]):
        where = f"{path} bases[{i}]"
        require_keys(base, ("x", "y", "orientation"), where)
        if base["orientation"] not in ORIENTATIONS:
            raise ConfigError(
                f"{where}: orientation debe ser {' o '.join(ORIENTATIONS)}"
            )
    return level


def load_entity_cfg(name: str, required: tuple[str, ...] = ()) -> dict:
    """Carga assets/cfg/<name>.json (jugador, enemigos, bases...) y valida sus claves."""
    path = os.path.join(CFG_DIR, f"{name}.json")
    cfg = load_json(path)
    require_keys(cfg, required, path)
    return cfg


def load_resources(path: str = os.path.join(CFG_DIR, "resources.json")) -> dict:
    """Carga resources.json comprobando que sus secciones sean objetos nombre -> ruta."""
    cfg = load_json(path)
    for section in RESOURCE_SECTIONS:
        if not isinstance(cfg.get(section, {}), dict):
            raise ConfigError(f"{path}: la sección {section} debe ser un objeto")
    return cfg
