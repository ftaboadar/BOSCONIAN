"""Funciones que ensamblan entidades a partir de componentes."""

import random

import esper
import pygame

from src.ecs.components.c_camera_target import CCameraTarget
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_star import CStar
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_enemy_state import INITIAL_STATE
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


def create_player_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Nave provisional (hito 3 la reemplaza): triángulo blanco de 12x12."""
    surf = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.polygon(surf, (255, 255, 255), [(6, 0), (12, 12), (0, 12)])
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(pygame.Vector2()), CSurface(surf),
        CWorld(), CCameraTarget(), CMinimapTrack("player"),
    )


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
    dev = cfg["deviation_degrees"]
    max_dev = dev["easy"] * (1 - difficulty) + dev["hard"] * difficulty
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
    )


def create_base_placeholder(world: esper.World, pos: pygame.Vector2) -> int:
    """Base provisional (hito 4 la reemplaza): cuadro rojo de 24x24."""
    surf = pygame.Surface((24, 24))
    surf.fill((200, 40, 40))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(surf), CWorld(), CMinimapTrack("base"),
    )
