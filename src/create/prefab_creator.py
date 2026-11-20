"""Funciones que ensamblan entidades a partir de componentes."""

import random

import esper
import pygame

from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_core import CBaseCore
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_enemy_bullet import CEnemyBullet
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_star import CStar
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_enemy_state import INITIAL_STATE
from src.engine.data_loader import load_json
from src.engine.service_locator import ServiceLocator, color_from_cfg


def create_image(world: esper.World, image_name: str, center: pygame.Vector2) -> int:
    return world.create_entity(
        CTransform(center),
        CSurface(ServiceLocator.images.get(image_name)),
    )


def create_text(world: esper.World, text: str, color: pygame.Color, center: pygame.Vector2) -> int:
    surf = ServiceLocator.fonts.get("main").render(text, False, color)
    return world.create_entity(CTransform(center), CSurface(surf))


def create_stars(world: esper.World, cfg: dict, area: pygame.Rect) -> None:
    speed = cfg["stars_blink_speed"]  # fija para todas; solo la fase difiere
    for _ in range(cfg["stars_number"]):
        c = random.choice(cfg["star_colors"])
        pos = pygame.Vector2(random.uniform(area.left, area.right - 1),
                             random.uniform(area.top, area.bottom - 1))
        world.create_entity(
            CTransform(pos),
            CStar(color_from_cfg(c),
                  speed,
                  random.random()),
        )


def create_hitbox(kind: str) -> CHitBox:
    """Crea la CHitBox de un tipo de entidad según la sección "hitboxes" de collisions.json."""
    cfg = load_json("assets/cfg/collisions.json")["hitboxes"][kind]
    offset = cfg.get("offset", {"x": 0, "y": 0})
    return CHitBox(pygame.Vector2(cfg["size"]["w"], cfg["size"]["h"]),
                   pygame.Vector2(offset["x"], offset["y"]),
                   cfg["layer"], tuple(cfg["mask"]))


def create_player_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Nave provisional (hito 3 la reemplaza): triángulo blanco de 12x12."""
    surf = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (255, 255, 255), [(6, 0), (12, 12), (0, 12)])
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2()), CSurface(surf),
        CWorld(), CCameraTarget(), CMinimapTrack("player"),
        create_hitbox("player"), CExplosive("player"),
    )


def _by_difficulty(span: dict, difficulty: float) -> float:
    """Valor entre `easy` (dificultad 0) y `hard` (dificultad 1)."""
    return span["easy"] * (1 - difficulty) + span["hard"] * difficulty


def create_enemy(world: esper.World, kind: str, pos: pygame.Vector2, direction: pygame.Vector2,
                 cfg: dict, player_speed: float, difficulty: float,
                 rng: random.Random | None = None) -> int:
    """Enemigo de tipo I, P o E (cuadro de color provisional) con su IA de estados.

    Va a `speed_factor` veces la velocidad del jugador. `difficulty` (0..1) fija cuánto
    se desvía al perseguir: entre la mitad y el máximo del rango, hacia un lado al azar.
    """
    rng = rng or random.Random()
    type_cfg = cfg["types"][kind]
    speed = player_speed * type_cfg["speed_factor"]
    surf = pygame.Surface((type_cfg["size"], type_cfg["size"]))
    surf.fill(color_from_cfg(type_cfg["color"]))
    max_dev = _by_difficulty(cfg["deviation_degrees"], difficulty)
    deviation = rng.choice((-1, 1)) * rng.uniform(max_dev / 2, max_dev)
    heading = pygame.Vector2(direction)
    if heading.length_squared() == 0:
        heading = pygame.Vector2(1, 0).rotate(rng.uniform(0, 360))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)),
        CVelocity(heading.normalize() * speed),
        CSurface(surf), CWorld(),
        CSteering(type_cfg.get("turn_rate", 0), deviation, type_cfg.get("wander")),
        CEnemyState(kind, INITIAL_STATE[kind], type_cfg.get("chase_seconds", 0)),
        CPoints(type_cfg["points"]),
    )


def create_enemy_spawner(world: esper.World, cfg: dict, difficulty: float) -> int:
    """Generador de enemigos del nivel. Con más `difficulty` (0..1) salen más seguido
    y se permiten más enemigos vivos a la vez."""
    spawn = cfg["spawn"]
    return world.create_entity(CEnemySpawner(
        _by_difficulty(spawn["interval_seconds"], difficulty),
        round(_by_difficulty(spawn["max_alive"], difficulty)),
        difficulty))


def _sprite(cfg: dict, rect: dict, quarter_turns: int,
            flip_x: bool = False, flip_y: bool = False) -> pygame.Surface:
    """Recorte de la hoja de sprites de las bases, con el colorkey transparente, espejado
    (si se pide) y girado."""
    sheet = ServiceLocator.images.get(cfg["image"])
    surf = sheet.subsurface(pygame.Rect(rect["x"], rect["y"], rect["w"], rect["h"])).copy()
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
    center = pygame.Rect(cfg["rect"]["x"], cfg["rect"]["y"], cfg["rect"]["w"], cfg["rect"]["h"]).center
    in_base = {"x": center[0] + off["x"] - closed["w"] //