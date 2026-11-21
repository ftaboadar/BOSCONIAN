"""Cargadores de datos: leen y validan los archivos JSON de assets/cfg."""

import json
import os
import re

CFG_DIR = "assets/cfg"
LEVELS_DIR = os.path.join(CFG_DIR, "levels")
LEVEL_FILE = re.compile(r"^level_(\d{2})\.json$")
ORIENTATIONS = ("horizontal", "vertical")
OBSTACLE_KINDS = ("rock", "mine", "solid_rock")
TURRETS_PER_BASE = 6
TURRET_FRAMES = 3  # cerrada, abierta y a punto de disparar
CORE_MODES = ("open", "cycle")  # siempre abierto sin disparar, o se abre y cierra
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
    if "difficulty" in level and (not isinstance(level["difficulty"], int) or level["difficulty"] < 1):
        raise ConfigError(f"{path}: difficulty debe ser un entero >= 1")
    for i, base in enumerate(level["bases"]):
        where = f"{path} bases[{i}]"
        require_keys(base, ("x", "y", "orientation"), where)
        if base["orientation"] not in ORIENTATIONS:
            raise ConfigError(
                f"{where}: orientation debe ser {' o '.join(ORIENTATIONS)}"
            )
    if not isinstance(level.get("special_shot", False), bool):
        raise ConfigError(f"{path}: special_shot debe ser true o false")
    if not isinstance(level.get("music", ""), str):
        raise ConfigError(f"{path}: music debe ser el nombre de una pista de resources.json")
    for kind, count in level.get("obstacles", {}).items():
        if kind not in OBSTACLE_KINDS:
            raise ConfigError(f"{path} obstacles: tipo desconocido {kind}")
        if not isinstance(count, int) or count < 0:
            raise ConfigError(f"{path} obstacles.{kind}: debe ser un entero >= 0")
    level.setdefault("special_shot", False)
    # Núcleo de las bases del nivel: siempre abierto, o con ciclo y lanzando enemigos E.
    level.setdefault("core_mode", "open")
    if level["core_mode"] not in CORE_MODES:
        raise ConfigError(f"{path}: core_mode debe ser {' o '.join(CORE_MODES)}")
    return level


def load_entity_cfg(name: str, required: tuple[str, ...] = ()) -> dict:
    """Carga assets/cfg/<name>.json (jugador, enemigos, bases...) y valida sus claves."""
    path = os.path.join(CFG_DIR, f"{name}.json")
    cfg = load_json(path)
    require_keys(cfg, required, path)
    return cfg


ENEMY_TYPE_KEYS = {
    "I": ("speed_factor", "turn_rate", "chase_seconds", "points", "spawn_weight", "size", "color"),
    "P": ("speed_factor", "turn_rate", "chase_seconds", "wander", "points", "spawn_weight", "size", "color"),
    "E": ("speed_factor", "points", "spawn_weight", "size", "color"),
}


def load_enemies() -> dict:
    """Carga enemies.json: tipos I, P y E y la sección `spawn`.

    Cada tipo debe ir más rápido que el jugador (speed_factor > 1) y tener un peso de
    spawn no negativo; al menos uno debe ser positivo para que pueda salir algún enemigo.
    """
    path = os.path.join(CFG_DIR, "enemies.json")
    cfg = load_entity_cfg("enemies", ("deviation_degrees", "spawn", "types"))
    require_keys(cfg["deviation_degrees"], ("easy", "hard"), f"{path} deviation_degrees")
    spawn = cfg["spawn"]
    require_keys(spawn, ("interval_seconds", "max_alive", "distance", "despawn_distance"),
                 f"{path} spawn")
    for key in ("interval_seconds", "max_alive"):
        require_keys(spawn[key], ("easy", "hard"), f"{path} spawn.{key}")
    if min(spawn["interval_seconds"]["easy"], spawn["interval_seconds"]["hard"]) <= 0:
        raise ConfigError(f"{path} spawn: interval_seconds debe ser mayor que 0")
    if min(spawn["max_alive"]["easy"], spawn["max_alive"]["hard"]) < 1:
        raise ConfigError(f"{path} spawn: max_alive debe ser al menos 1")
    if spawn["despawn_distance"] <= spawn["distance"]:
        raise ConfigError(f"{path} spawn: despawn_distance debe ser mayor que distance")
    require_keys(cfg["types"], tuple(ENEMY_TYPE_KEYS), f"{path} types")
    unknown = [k for k in cfg["types"] if k not in ENEMY_TYPE_KEYS]
    if unknown:
        raise ConfigError(f"{path} types: tipos desconocidos {', '.join(unknown)}")
    for kind, keys in ENEMY_TYPE_KEYS.items():
        where = f"{path} types.{kind}"
        require_keys(cfg["types"][kind], keys, where)
        if cfg["types"][kind]["speed_factor"] <= 1:
            raise ConfigError(f"{where}: speed_factor debe ser mayor que 1")
    weights = [t["spawn_weight"] for t in cfg["types"].values()]
    if min(weights) < 0 or sum(weights) <= 0:
        raise ConfigError(f"{path} types: spawn_weight no puede ser negativo ni todos cero")
    require_keys(cfg["types"]["P"]["wander"], ("distance", "radius", "jitter"),
                 f"{path} types.P.wander")
    return cfg


def _require_rects(rects: list, source: str) -> None:
    for i, rect in enumerate(rects):
        require_keys(rect, ("x", "y", "w", "h"), f"{source}[{i}]")


def load_bases() -> dict:
    """Carga bases.json: puntos, sprite de la base, sus seis torretas (con sus cuadros y
    su disparo), las balas y el núcleo (cuadros y ciclo de apertura)."""
    path = os.path.join(CFG_DIR, "bases.json")
    cfg = load_entity_cfg("bases", ("points", "image", "colorkey", "rect", "turret",
                                    "bullet", "core"))
    require_keys(cfg["points"], ("base", "turret"), f"{path} points")
    require_keys(cfg["colorkey"], ("r", "g", "b"), f"{path} colorkey")
    require_keys(cfg["rect"], ("x", "y", "w", "h"), f"{path} rect")
    turret = cfg["turret"]
    require_keys(turret, ("radius", "wreck_rect", "offsets", "frames", "range",
                          "fire_interval", "warn_seconds"), f"{path} turret")
    require_keys(turret["wreck_rect"], ("x", "y", "w", "h"), f"{path} turret.wreck_rect")
    if not isinstance(turret["offsets"], list) or len(turret["offsets"]) != TURRETS_PER_BASE:
        raise ConfigError(f"{path} turret.offsets: deben ser {TURRETS_PER_BASE} torretas")
    for i, offset in enumerate(turret["offsets"]):
        require_keys(offset, ("x", "y"), f"{path} turret.offsets[{i}]")
    if not isinstance(turret["frames"], list) or len(turret["frames"]) != TURRET_FRAMES:
        raise ConfigError(f"{path} turret.frames: deben ser {TURRET_FRAMES} cuadros")
    _require_rects(turret["frames"], f"{path} turret.frames")
    require_keys(turret["fire_interval"], ("min", "max"), f"{path} turret.fire_interval")
    if not 0 < turret["fire_interval"]["min"] <= turret["fire_interval"]["max"]:
        raise ConfigError(f"{path} turret.fire_interval: debe cumplirse 0 < min <= max")
    require_keys(cfg["bullet"], ("speed", "seconds", "size", "color"), f"{path} bullet")
    require_keys(cfg["bullet"]["color"], ("r", "g", "b"), f"{path} bullet.color")
    core = cfg["core"]
    require_keys(core, ("radius", "frames", "closed_seconds", "open_seconds", "frame_seconds"),
                 f"{path} core")
    if not isinstance(core["frames"], list) or len(core["frames"]) < 2:
        raise ConfigError(f"{path} core.frames: al menos 2 cuadros (cerrado y abierto)")
    _require_rects(core["frames"], f"{path} core.frames")
    require_keys(core["closed_seconds"], ("easy", "hard"), f"{path} core.closed_seconds")
    if min(core["frame_seconds"], core["open_seconds"]) <= 0:
        raise ConfigError(f"{path} core: frame_seconds y open_seconds deben ser mayores que 0")
    if min(core["closed_seconds"]["easy"], core["closed_seconds"]["hard"]) < 0:
        raise ConfigError(f"{path} core: closed_seconds no puede ser negativo")
    return cfg


def load_resources(path: str = os.path.join(CFG_DIR, "resources.json")) -> dict:
    """Carga resources.json comprobando que sus secciones sean objetos nombre -> ruta."""
    cfg = load_json(path)
    for section in RESOURCE_SECTIONS:
        if not isinstance(cfg.get(section, {}), dict):
            raise ConfigError(f"{path}: la sección {section} debe ser un objeto")
    return cfg
