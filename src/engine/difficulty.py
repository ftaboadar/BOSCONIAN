"""Dificultad única por nivel: traduce el valor del JSON a los tiempos de las alertas y a un
factor 0..1 con el que spawn, steering y núcleos interpolan entre sus valores easy y hard."""

from src.engine.data_loader import ConfigError, load_json, require_keys

PATH = "assets/cfg/difficulty.json"
PARAMS = ("yellow_after", "red_after")
# Alertas, igual en todos los niveles: segundos en VERDE tras destruir una base y cuánto
# más rápidos y más seguidos salen los enemigos en ROJA.
ALERT_PARAMS = ("calm_seconds", "red_speed_factor", "red_spawn_factor")


def difficulty_params(level: dict) -> dict:
    """Parámetros del nivel `level` (dict cargado). Sin `difficulty`, usa el valor por defecto.

    Incluye los de las alertas: los tiempos del nivel y los comunes de la sección `alert`."""
    cfg = load_json(PATH)
    require_keys(cfg, ("default", "levels", "alert"), PATH)
    require_keys(cfg["alert"], ALERT_PARAMS, f"{PATH} alert")
    for key in ALERT_PARAMS:
        if cfg["alert"][key] <= 0:
            raise ConfigError(f"{PATH}: alert.{key} debe ser mayor que 0")
    table = {int(k): v for k, v in cfg["levels"].items()}
    if not table:
        raise ConfigError(f"{PATH}: levels está vacío")
    value = level.get("difficulty", cfg["default"])
    value = min(max(value, min(table)), max(table))  # acota al rango definido
    row = table[value]
    require_keys(row, PARAMS, f"{PATH} nivel {value}")
    if not 0 < row["yellow_after"] < row["red_after"]:
        raise ConfigError(f"{PATH} nivel {value}: debe cumplirse 0 < yellow_after < red_after")
    return {"difficulty": value, **cfg["alert"], **row}


def difficulty_factor(params: dict) -> float:
    """Dificultad como número 0..1 (nivel mínimo = 0, máximo = 1), para interpolar easy/hard."""
    cfg = load_json(PATH)
    levels = [int(k) for k in cfg["levels"]]
    lo, hi = min(levels), max(levels)
    return 0.0 if hi == lo else (params["difficulty"] - lo) / (hi - lo)
