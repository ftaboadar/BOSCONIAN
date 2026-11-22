"""Funciones que ensamblan entidades a partir de componentes."""

import functools
import math
import random

import esper
import pygame

from src.ecs.components.c_ability import CAbility, CAbilityItem, CItemSpawner, CShieldAura
from src.ecs.components.c_alert import CAlert
from src.ecs.components.c_angle_sprites import CAngleSprites
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_core import CBaseCore
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_enemy_bullet import CEnemyBullet
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_level_clock import CLevelClock
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_player_bullet import CPlayerBullet
from src.ecs.components.c_player_ship import CHeadingSprites, CPlayerShip
from src.ecs.components.c_star import CStar
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_weapon import CWeapon
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_enemy_sprite import heading_index
from src.engine.data_loader import load_json
from src.engine.service_locator import ServiceLocator, color_from_cfg, rect_from_cfg


@functools.cache
def logo_cfg() -> dict:
    """Sección "logo" de story.json (qué imagen es y cómo limpiarla), leída una sola vez."""
    return load_json("assets/cfg/story.json")["logo"]


def logo_surface(width: int | None = None) -> pygame.Surface:
    """El logo del juego listo para dibujar: sin el rectángulo blanco translúcido que trae la
    imagen (se vería como una mancha sobre el verde) y, si se pide, a `width` px de ancho.
    Es halo todo píxel casi blanco (`halo_min_white`) y casi transparente (`halo_max_alpha`)."""
    cfg = logo_cfg()
    max_alpha, white = cfg["halo_max_alpha"], cfg["halo_min_white"]
    surf = ServiceLocator.images.get(cfg["image"]).copy()
    for x in range(surf.get_width()):
        for y in range(surf.get_height()):
            r, g, b, a = surf.get_at((x, y))
            if 0 < a < max_alpha and r > white and g > white and b > white:
                surf.set_at((x, y), (0, 0, 0, 0))  # transparente y sin color: el blanco se colaría al reducir
    return scaled_to_width(surf, width) if width and width != surf.get_width() else surf


def scaled_to_width(surf: pygame.Surface, width: int) -> pygame.Surface:
    """La imagen a `width` px de ancho, conservando la proporción y suavizando el escalado."""
    height = max(1, round(surf.get_height() * width / surf.get_width()))
    return pygame.transform.smoothscale(surf, (width, height))


def create_image(world: esper.World, image_name: str, center: pygame.Vector2,
                 width: int | None = None) -> int:
    """Imagen de interfaz centrada en `center`; con `width` se reduce (o amplía) a ese ancho."""
    surf = ServiceLocator.images.get(image_name)
    if width is not None:
        surf = scaled_to_width(surf, width)
    return world.create_entity(CTransform(center), CSurface(surf))


def create_text(world: esper.World, text: str, color: pygame.Color, center: pygame.Vector2) -> int:
    surf = ServiceLocator.fonts.get("main").render(text, False, color)
    return world.create_entity(CTransform(center), CSurface(surf))


def create_special_shot_message(world: esper.World, cfg: dict, active: bool, center_x: float) -> int:
    """Aviso temporal al inicio del nivel que indica si el disparo especial está activo."""
    m = cfg["special_message"]
    key = "active" if active else "inactive"
    entity = create_text(world, m[f"{key}_text"], color_from_cfg(m[f"{key}_color"]),
                         pygame.Vector2(center_x, m["y"]))
    world.add_component(entity, CLifetime(m["duration"]))
    return entity


def create_score_popup(world: esper.World, pos: pygame.Vector2, points: int, cfg: dict) -> int:
    """Cartel con los puntos ganados, en el lugar donde se destruyó algo.

    Sube despacio y desaparece solo pasado `cfg["seconds"]`. Es una entidad del mundo: se
    mueve con la cámara, no con la pantalla."""
    surf = ServiceLocator.fonts.get("main").render(str(points), False, color_from_cfg(cfg["color"]))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2(0, -cfg["rise_speed"])),
        CSurface(surf), CWorld(), CLifetime(cfg["seconds"]),
    )


def create_stars(world: esper.World, cfg: dict, area: pygame.Rect) -> None:
    speed = cfg["stars_blink_speed"]  # fija para todas; solo la fase difiere
    for _ in range(cfg["stars_number"]):
        c = random.choice(cfg["star_colors"])
        pos = pygame.Vector2(random.uniform(area.left, area.right - 1),
                             random.uniform(area.top, area.bottom - 1))
        surf = pygame.Surface((1, 1), pygame.SRCALPHA)
        surf.fill(color_from_cfg(c))
        world.create_entity(CTransform(pos), CStar(surf, speed, random.random()))


@functools.cache
def _hitboxes_cfg() -> dict:
    """Sección "hitboxes" de collisions.json, leída de disco una sola vez."""
    return load_json("assets/cfg/collisions.json")["hitboxes"]


def create_hitbox(kind: str) -> CHitBox:
    """Crea la CHitBox de un tipo de entidad según la sección "hitboxes" de collisions.json.

    Cada llamada devuelve una CHitBox nueva (create_base, por ejemplo, gira su tamaño),
    pero el JSON se lee de disco una sola vez.
    """
    cfg = _hitboxes_cfg()[kind]
    offset = cfg.get("offset", {"x": 0, "y": 0})
    return CHitBox(pygame.Vector2(cfg["size"]["w"], cfg["size"]["h"]),
                   pygame.Vector2(offset["x"], offset["y"]),
                   cfg["layer"], tuple(cfg["mask"]))


def heading_sprites(base: pygame.Surface) -> dict[tuple[int, int], pygame.Surface]:
    """Las 8 variantes de un sprite que mira hacia arriba, una por cada (dx, dy) de rumbo."""
    # Ángulo antihorario de pygame.transform.rotate para cada (dx, dy) con "arriba" = (0, -1).
    return {
        (dx, dy): pygame.transform.rotate(base, round(math.degrees(math.atan2(-dx, -dy))))
        for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)
    }


def angle_sprites(base: pygame.Surface, steps: int) -> list[pygame.Surface]:
    """`steps` variantes de un sprite que mira hacia arriba, girado en pasos iguales en sentido
    horario (con 16, cada 22,5 grados)."""
    return [pygame.transform.rotate(base, -k * 360 / steps) for k in range(steps)]


def create_player(world: esper.World, pos: pygame.Vector2, cfg: dict, special: bool = False) -> int:
    """Nave del jugador: sprite único hacia arriba, rotado en pasos de 45 grados.

    `special` activa el disparo especial (lo define el nivel)."""
    base = ServiceLocator.images.get("ships").subsurface(rect_from_cfg(cfg["sprite_rect"])).copy()
    sprites = heading_sprites(base)
    w = cfg["weapon"]
    heading = (cfg["start_heading"]["x"], cfg["start_heading"]["y"])
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2()), CSurface(sprites[heading]),
        CWorld(), CCameraTarget(), CMinimapTrack("player"),
        create_hitbox("player"), CExplosive("player"),
        CPlayerShip(heading, cfg["max_speed"], cfg["acceleration"]), CHeadingSprites(sprites),
        CWeapon(w["cooldown"], w["bullet_speed"], w["muzzle_offset"], _bullet_sprites(w),
                 special, w["special_spread"]),
    )


def _bullet_sprites(weapon_cfg: dict) -> dict[tuple[int, int], pygame.Surface]:
    """Sprite de bala para cada una de las 8 direcciones a partir de vertical, horizontal y diagonal."""
    sheet = ServiceLocator.images.get("ships")

    def cut(name: str) -> pygame.Surface:
        return sheet.subsurface(rect_from_cfg(weapon_cfg["bullet_sprites"][name])).copy()

    vertical, horizontal, diagonal = cut("vertical"), cut("horizontal"), cut("diagonal")
    sprites = {}
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if (dx, dy) == (0, 0):
                continue
            if dx == 0:
                sprites[(dx, dy)] = vertical
            elif dy == 0:
                sprites[(dx, dy)] = horizontal
            else:  # el sprite diagonal original es "/" (arriba-derecha / abajo-izquierda)
                sprites[(dx, dy)] = diagonal if dx * dy < 0 else pygame.transform.flip(diagonal, True, False)
    return sprites


def create_player_bullet(world: esper.World, pos: pygame.Vector2, vel: pygame.Vector2,
                         surf: pygame.Surface) -> int:
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2(vel)), CSurface(surf),
        CWorld(), CPlayerBullet(), create_hitbox("player_bullet"),
    )


def _by_difficulty(span: dict, difficulty: float) -> float:
    """Valor entre `easy` (dificultad 0) y `hard` (dificultad 1)."""
    return span["easy"] * (1 - difficulty) + span["hard"] * difficulty


def create_enemy(world: esper.World, kind: str, pos: pygame.Vector2, direction: pygame.Vector2,
                 cfg: dict, player_speed: float, difficulty: float,
                 rng: random.Random | None = None) -> int:
    """Enemigo de tipo I, P o E con su sprite (que gira hacia donde va) y su IA de estados.

    Va a `speed_factor` veces la velocidad del jugador. `difficulty` (0..1) fija cuánto
    se desvía al perseguir: entre la mitad y el máximo del rango, hacia un lado al azar.
    """
    rng = rng or random.Random()
    type_cfg = cfg["types"][kind]
    speed = player_speed * type_cfg["speed_factor"]
    sprite = ServiceLocator.images.get("ships").subsurface(rect_from_cfg(type_cfg["sprite"])).copy()
    steps = cfg["heading_steps"]
    sprites = angle_sprites(sprite, steps)
    max_dev = _by_difficulty(cfg["deviation_degrees"], difficulty)
    deviation = rng.choice((-1, 1)) * rng.uniform(max_dev / 2, max_dev)
    after_chase = type_cfg.get("after_chase")
    heading = pygame.Vector2(direction)
    if heading.length_squared() == 0:
        heading = pygame.Vector2(1, 0).rotate(rng.uniform(0, 360))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)),
        CVelocity(heading.normalize() * speed),
        CSurface(sprites[heading_index(heading, steps)]), CAngleSprites(sprites), CWorld(),
        CSteering(type_cfg.get("turn_rate", 0), deviation, type_cfg.get("wander")),
        CEnemyState(kind, EnemyState[type_cfg["initial_state"]], type_cfg.get("chase_seconds", 0),
                    EnemyState[after_chase] if after_chase else None),
        CPoints(type_cfg["points"]), create_hitbox("enemy"), CExplosive("simple"),
    )


def create_enemy_spawner(world: esper.World, cfg: dict, difficulty: float) -> int:
    """Generador de enemigos del nivel. Con más `difficulty` (0..1) salen más seguido
    y se permiten más enemigos vivos a la vez."""
    spawn = cfg["spawn"]
    return world.create_entity(CEnemySpawner(
        _by_difficulty(spawn["interval_seconds"], difficulty),
        round(_by_difficulty(spawn["max_alive"], difficulty)),
        difficulty))


def create_alert(world: esper.World, params: dict) -> int:
    """Condición de alerta del nivel, con los tiempos de su dificultad (`difficulty_params`)."""
    return world.create_entity(CAlert(
        params["yellow_after"], params["red_after"], params["calm_seconds"],
        params["red_speed_factor"], params["red_spawn_factor"]))


def create_level_clock(world: esper.World, blast_seconds: float, death_wait: float) -> int:
    """Cuentas del nivel: BLAST OFF! al empezar y la espera tras la muerte del jugador."""
    return world.create_entity(CLevelClock(blast_seconds, death_wait))


def _sprite(cfg: dict, rect: dict, quarter_turns: int,
            flip_x: bool = False, flip_y: bool = False) -> pygame.Surface:
    """Recorte de la hoja de sprites de las bases, con el colorkey transparente, espejado
    (si se pide) y girado."""
    sheet = ServiceLocator.images.get(cfg["image"])
    surf = sheet.subsurface(rect_from_cfg(rect)).copy()
    key = color_from_cfg(cfg["colorkey"])
    pixels = pygame.PixelArray(surf)
    pixels.replace(key, pygame.Color(0, 0, 0, 0))
    pixels.close()
    return pygame.transform.rotate(pygame.transform.flip(surf, flip_x, flip_y), 90 * quarter_turns)


def _turret_frames(cfg: dict, off: dict, turns: int) -> list[pygame.Surface]:
    """Cuadros de la torreta que está en `off`: cerrada, abierta y a punto de disparar.

    Cerrada es tal cual viene dibujada en el sprite de la base; los otros cuadros de la
    hoja son los de la torreta de arriba a la izquierda, espejados para las demás.
    """
    closed, *others = cfg["turret"]["frames"]
    center = rect_from_cfg(cfg["rect"]).center
    in_base = {"x": center[0] + off["x"] - closed["w"] // 2,
               "y": center[1] + off["y"] - closed["h"] // 2, "w": closed["w"], "h": closed["h"]}
    return [_sprite(cfg, in_base, turns)] + [
        _sprite(cfg, r, turns, off["x"] > 0, off["y"] > 0) for r in others]


def create_base(world: esper.World, pos: pygame.Vector2, orientation: str, cfg: dict,
                core_mode: str = "open", difficulty: float = 0.0,
                rng: random.Random | None = None, index: int = 0) -> int:
    """Base enemiga quieta en `pos`: una entidad con el sprite completo más una entidad
    por cada una de sus seis torretas, otra por el núcleo y una por cada pieza del cuerpo
    contra la que se choca (sin sprite propio). `index` es su posición en el nivel.

    bases.json describe la base vertical (abierta arriba y abajo, así que el núcleo
    se alcanza con un disparo vertical); la horizontal es la misma girada 90 grados.
    Cada torreta dispara a un intervalo propio, al azar dentro de `turret.fire_interval`.
    Con `core_mode` "cycle" el núcleo se abre y se cierra (pasa menos tiempo cerrado
    con más `difficulty`, 0..1); con "open" queda siempre abierto.
    """
    rng = rng or random.Random()
    turns = 0 if orientation == "vertical" else 1
    turret, core = cfg["turret"], cfg["core"]
    core_frames = [_sprite(cfg, r, turns) for r in core["frames"]]
    base = world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(_sprite(cfg, cfg["rect"], turns)), CWorld(),
        CMinimapTrack("base"), CPoints(cfg["points"]["base"]), CExplosive("base"),
        CBase(orientation, _sprite(cfg, turret["wreck_rect"], turns), turret["radius"],
              core_frames, core["radius"], index),
    )
    # El cuerpo no es un rectángulo: el sprite es un anillo con huecos. Cada pieza sólida
    # (las de collisions.json son las de la base vertical) es una hitbox aparte.
    body = _hitboxes_cfg()["base"]
    for box in body["boxes"]:
        offset = pygame.Vector2(box["x"], box["y"]).rotate(-90 * turns)
        size = (box["h"], box["w"]) if turns else (box["w"], box["h"])
        world.create_entity(CTransform(pos + offset), CBasePart(base, "body", offset),
                            CHitBox(pygame.Vector2(size), None, body["layer"], tuple(body["mask"])))
    for off in turret["offsets"]:
        offset = pygame.Vector2(off["x"], off["y"]).rotate(-90 * turns)
        interval = rng.uniform(turret["fire_interval"]["min"], turret["fire_interval"]["max"])
        world.create_entity(CTransform(pos + offset), CWorld(),
                            CBasePart(base, "turret", offset), CPoints(cfg["points"]["turret"]),
                            CTurret(interval, _turret_frames(cfg, off, turns)),
                            create_hitbox("base_turret"), CExplosive("turret"))
    core_ent = world.create_entity(CTransform(pygame.Vector2(pos)), CWorld(),
                                   CBasePart(base, "core", pygame.Vector2()),
                                   create_hitbox("base_core"))
    if core_mode == "cycle":
        # El sprite de la base trae el núcleo abierto: empieza en el último cuadro.
        world.add_component(core_ent, CBaseCore(
            _by_difficulty(core["closed_seconds"], difficulty), core["open_seconds"],
            core["frame_seconds"], len(core_frames) - 1))
    return base


def create_enemy_bullet(world: esper.World, pos: pygame.Vector2, vel: pygame.Vector2,
                        cfg: dict) -> int:
    """Bala pequeña de torreta (cuadro de color) que dura `seconds` (CLifetime)."""
    surf = pygame.Surface((cfg["size"], cfg["size"]))
    surf.fill(color_from_cfg(cfg["color"]))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2(vel)), CSurface(surf),
        CWorld(), CEnemyBullet(), CLifetime(cfg["seconds"]), create_hitbox("enemy_bullet"),
    )


def create_explosion(world: esper.World, pos: pygame.Vector2, vel: pygame.Vector2,
                     cfg: dict) -> int:
    """Explosión animada que conserva la velocidad de la entidad destruida.

    cfg es un tipo de explosions.json (por ejemplo cfg["simple"]). La animación
    no se repite: al terminar, system_animation marca la entidad con CDestroy.
    Si el tipo tiene "hitbox", la explosión mata lo que toque mientras dura.
    """
    sheet = ServiceLocator.images.get(cfg["image"])
    frames = [rect_from_cfg(f) for f in cfg["frames"]]
    ent = world.create_entity(
        CTransform(pygame.Vector2(pos)),
        CVelocity(pygame.Vector2(vel)),
        CSurface(sheet.subsurface(frames[0])),
        CAnimation(sheet, frames, cfg["framerate"], loop=False),
        CWorld(),
    )
    if "hitbox" in cfg:  # explosión letal (por ejemplo, la de las minas)
        world.add_component(ent, create_hitbox(cfg["hitbox"]))
    return ent


def equip_ability(world: esper.World, player: int, cfg: dict) -> None:
    """Da a la nave la segunda habilidad (escudo, ability.json) con los usos con que empieza."""
    shield = cfg["shield"]
    world.add_component(player, CAbility(shield["max_charges"], shield["duration"], shield["start_charges"]))


def create_ability_item_spawner(world: esper.World, cfg: dict, chance: float) -> int:
    """Generador de ítems de la habilidad: `chance` (0..1) es la probabilidad por intervalo y la fija el nivel."""
    return world.create_entity(CItemSpawner(cfg["item"]["interval_seconds"], chance))


def create_ability_item(world: esper.World, pos: pygame.Vector2, item_cfg: dict) -> int:
    """Ítem del escudo: un disco con borde, con vida limitada; aparece en el minimapa como `item`."""
    size = item_cfg["size"]
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    pygame.draw.circle(surf, color_from_cfg(item_cfg["color"]), center, size // 2)
    pygame.draw.circle(surf, color_from_cfg(item_cfg["core_color"]), center, size // 2, 1)
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(surf), CWorld(), CAbilityItem(),
        CMinimapTrack("item"), create_hitbox("ability_item"), CLifetime(item_cfg["lifetime_seconds"]),
    )


def create_shield_aura(world: esper.World, owner: int, shield_cfg: dict) -> int:
    """Anillo alrededor de la nave mientras dura el escudo (entidad del mundo, sigue a `owner`)."""
    r = shield_cfg["radius"]
    ring = pygame.Surface((2 * r + 1, 2 * r + 1), pygame.SRCALPHA)
    pygame.draw.circle(ring, color_from_cfg(shield_cfg["color"]), (r, r), r, 1)
    blank = pygame.Surface(ring.get_size(), pygame.SRCALPHA)
    return world.create_entity(
        CTransform(pygame.Vector2(world.component_for_entity(owner, CTransform).pos)), CSurface(ring),
        CWorld(), CShieldAura(owner, ring, blank, shield_cfg["blink_seconds"], shield_cfg["blink_rate"]),
    )
