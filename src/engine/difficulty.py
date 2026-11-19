"""Dificultad única por nivel: traduce el valor del JSON a parámetros para spawn, steering y alertas."""

from src.engine.data_loader import ConfigError, load_json, require_keys

PATH = "assets/cfg/difficulty.json"
PARAMS = ("spawn_interval", "steer_deviation", "yellow_after", "red_after")


def difficulty_params(level: dict) -> dict:
    """Parámetros del nivel `level` (dict cargado). Sin `difficulty`, usa el valor por defecto."""
    cfg = load_json(PATH)
    require_keys(cfg, ("default", "levels"), PATH)
    table = {int(k): v for k, v in cfg["levels"].items()}
    if not table:
        raise ConfigError(f"{PATH}: levels está vacío")
    value = level.get("difficulty", cfg["default"])
    value = min(max(value, min(table)), max(table))  # acota al rango definido
    row = table[value]
    require_keys(row, PARAMS, f"{PATH} nivel {value}")
    return {"difficulty": value, **row}
