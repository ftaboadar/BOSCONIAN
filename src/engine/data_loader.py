"""Cargadores de datos: leen y validan los archivos JSON de assets/cfg."""

import copy
import json
import os
import re

CFG_DIR = "assets/cfg"
LEVELS_DIR = os.path.join(CFG_DIR, "levels")
LEVEL_FILE = re.compile(r"^level_(\d{2})\.json$")
ORIENTATIONS = ("horizontal", "vertical")
SUBTITLE_MAX = 24  # letras que caben en el campo de juego (192 px / 8 px por letra)
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
    return validate_level(load_json(path), path)


def validate_level(level: dict, path: str) -> dict:
    """Valida un nivel (cargado o armado por el editor) y le pone los valores por defecto.

    `path` solo sirve para nombrar el origen en los mensajes de error."""
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
    if "subtitle" in level and (not isinstance(level["subtitle"], str) or len(level["subtitle"]) > SUBTITLE_MAX):
        raise ConfigError(f"{path}: subtitle debe ser un texto de a lo sumo {SUBTITLE_MAX} letras")
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


LEVEL_KEY_ORDER = ("round", "subtitle", "difficulty", "core_mode", "player_start", "bases", "obstacles",
                   "special_shot", "music")


def _point(p: dict) -> str:
    return "{ " + ", ".join(f'"{k}": {json.dumps(v)}' for k, v in p.items()) + " }"


def format_level(level: dict) -> str:
    """Texto JSON de un nivel con el mismo estilo que los archivos de assets/cfg/levels:
    una línea por base y por punto, y las claves en un orden fijo."""
    keys = [k for k in LEVEL_KEY_ORDER if k in level] + [k for k in level if k not in LEVEL_KEY_ORDER]
    lines = []
    for key in keys:
        value = level[key]
        if key == "bases":
            rows = ",\n".join("        " + _point(b) for b in value)
            lines.append(f'    "bases": [\n{rows}\n    ]' if value else '    "bases": []')
        elif isinstance(value, dict):
            lines.append(f'    "{key}": {_point(value)}')
        else:
            lines.append(f'    "{key}": {json.dumps(value)}')
    return "{\n" + ",\n".join(lines) + "\n}\n"


def save_level(number: int, level: dict) -> str:
    """Valida y guarda el nivel `number` en su archivo (lo crea si no existe) y devuelve la ruta.

    Si el nivel no es válido lanza ConfigError y no toca el archivo existente. La escritura es
    atómica: el archivo nunca queda a medias."""
    path = level_path(number)
    validate_level(copy.deepcopy(level), path)
    os.makedirs(LEVELS_DIR, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(format_level(level))
    os.replace(tmp, path)
    return path


def load_entity_cfg(name: str, required: tuple[str, ...] = ()) -> dict:
    """Carga assets/cfg/<name>.json (jugador, enemigos, bases...) y valida sus claves."""
    path = os.path.join(CFG_DIR, f"{name}.json")
    cfg = load_json(path)
    require_keys(cfg, required, path)
    return cfg


ENEMY_TYPE_KEYS = {
    "I": ("speed_factor", "turn_rate", "initial_state", "chase_seconds", "after_chase", "points",
          "spawn_weight", "sprite"),
    "P": ("speed_factor", "turn_rate", "initial_state", "chase_seconds", "after_chase", "wander",
          "points", "spawn_weight", "sprite"),
    "E": ("speed_factor", "initial_state", "points", "spawn_weight", "sprite"),
}
ENEMY_STATES = ("CHASE", "LEAVE", "WANDER", "STRAIGHT")  # los de EnemyState (c_enemy_state.py)


def load_enemies() -> dict:
    """Carga enemies.json: tipos I, P y E (con su máquina de estados) y la sección `spawn`.

    Cada tipo debe ir más rápido que el jugador (speed_factor > 1) y tener un peso de
    spawn no negativo; al menos uno debe ser positivo para que pueda salir algún enemigo.
    """
    path = os.path.join(CFG_DIR, "enemies.json")
    cfg = load_entity_cfg("enemies", ("deviation_degrees", "spawn", "types", "heading_steps"))
    steps = cfg["heading_steps"]
    if not isinstance(steps, int) or steps < 8:
        raise ConfigError(f"{path}: heading_steps debe ser un entero >= 8 (16 como el original)")
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
        require_keys(cfg["types"][kind]["sprite"], ("x", "y", "w", "h"), f"{where}.sprite")
        if cfg["types"][kind]["speed_factor"] <= 1:
            raise ConfigError(f"{where}: speed_factor debe ser mayor que 1")
        # Máquina de estados del tipo: con cuál nace y a cuál pasa al acabar la persecución.
        for key in ("initial_state", "after_chase"):
            if cfg["types"][kind].get(key, ENEMY_STATES[0]) not in ENEMY_STATES:
                raise ConfigError(f"{where}: {key} debe ser uno de {', '.join(ENEMY_STATES)}")
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


STORY_EVENT_KEYS = {
    "image": ("image",),
    "sprite": ("rect",),
    "box": ("size", "color"),
    "text": ("text",),
    "frames": ("image", "rects", "framerate", "pos"),
    "sound": ("sound",),
}
MOVING_EVENT_TYPES = ("image", "sprite", "box", "text")  # se mueven de `from` a `to` en `seconds`
STORY_SCENES = ("splash", "logo_slide", "byline", "cutscene")  # escenas que corren solas
STORY_SECTIONS = STORY_SCENES + ("title",)  # el título también usa eventos, pero lo maneja él


def load_story() -> dict:
    """Carga story.json: las líneas de tiempo del arranque (pantalla inicial, logo, créditos y
    título) y de la cinemática antes de cada nivel.

    Las escenas que corren solas (STORY_SCENES) tienen `next`, `duration`, `stars_speed` y los
    `events`; el título solo trae `events`. Un error de configuración se reporta aquí, con el
    evento que lo causa, y no a mitad de la animación.
    """
    path = os.path.join(CFG_DIR, "story.json")
    cfg = load_entity_cfg("story", ("grace_seconds", "logo") + STORY_SECTIONS)
    require_keys(cfg["logo"], ("image", "halo_max_alpha", "halo_min_white"), f"{path} logo")
    colors = load_json(os.path.join(CFG_DIR, "menu.json"))["colors"]
    for name in STORY_SECTIONS:
        scene = cfg[name]
        require_keys(scene, ("events",), f"{path} {name}")
        timed = name in STORY_SCENES
        if timed:
            require_keys(scene, ("next", "duration", "stars_speed"), f"{path} {name}")
            if scene["duration"] <= 0:
                raise ConfigError(f"{path} {name}: duration debe ser mayor que 0")
        for i, event in enumerate(scene["events"]):
            where = f"{path} {name}.events[{i}]"
            require_keys(event, ("at", "type"), where)
            if event["type"] not in STORY_EVENT_KEYS:
                raise ConfigError(f"{where}: tipo desconocido {event['type']}")
            require_keys(event, STORY_EVENT_KEYS[event["type"]], where)
            if event["at"] < 0 or (timed and event["at"] > scene["duration"]):
                raise ConfigError(f"{where}: at debe estar entre 0 y la duración de la escena")
            if "width" in event and (not isinstance(event["width"], int) or event["width"] <= 0):
                raise ConfigError(f"{where}: width debe ser un entero mayor que 0")
            if event["type"] == "text" and isinstance(event.get("color"), str) and event["color"] not in colors:
                raise ConfigError(f"{where}: color desconocido {event['color']}")
            if event["type"] in MOVING_EVENT_TYPES and "to" in event:
                require_keys(event, ("from", "seconds"), where)
                if event["seconds"] <= 0:
                    raise ConfigError(f"{where}: seconds debe ser mayor que 0")
            elif event["type"] in ("sprite", "box", "image", "text"):
                require_keys(event, ("pos",), where)  # sin movimiento, se queda en `pos`
    return cfg
