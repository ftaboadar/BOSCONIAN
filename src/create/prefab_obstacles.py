"""Prefabs de obstáculos: rocas, minas y rocas indestructibles (#24)."""

import random

import esper
import pygame

from src.create.prefab_creator import create_hitbox
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.engine.camera import wrap_delta
from src.engine.service_locator import ServiceLocator

def _rect(r: dict) -> pygame.Rect:
    return pygame.Rect(r["x"], r["y"], r["w"], r["h"])


def _random_sprite(cfg: dict) -> pygame.Surface:
    sheet = ServiceLocator.images.get(cfg["image"])
    return sheet.subsurface(_rect(random.choice(cfg["sprites"])))


def create_rock(world: esper.World, pos: pygame.Vector2, cfg: dict) -> int:
    """Roca estática y destructible: da puntos y explota."""
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(_random_sprite(cfg)), CWorld(),
        create_hitbox("rock"), CPoints(cfg["points"]), CExplosive("simple"),
    )


def create_mine(world: esper.World, pos: pygame.Vector2, cfg: dict) -> int:
    """Mina estática con luces animadas; su explosión es letal."""
    sheet = ServiceLocator.images.get(cfg["image"])
    frames = [_rect(f) for f in cfg["frames"]]
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CSurface(sheet.subsurface(frames[0])), CWorld(),
        CAnimation(sheet, frames, cfg["framerate"], loop=True),
        create_hitbox("mine"), CPoints(cfg["points"]), CExplosive("mine"),
    )


def create_solid_rock(world: esper.World, pos: pygame.Vector2, cfg: dict) -> int:
    """Roca indestructible que se mueve en una dirección al azar."""
    vel = pygame.Vector2(cfg["speed"], 0).rotate(random.uniform(0, 360))
    return world.create_entity(
        CTransform(pygame.Vector2(pos)), CVelocity(vel), CSurface(_random_sprite(cfg)),
        CWorld(), create_hitbox("solid_rock"),
    )


CREATORS = {"rock": create_rock, "mine": create_mine, "solid_rock": create_solid_rock}


def create_obstacles(world: esper.World, level: dict, cfg: dict,
                     world_size: pygame.Vector2) -> None:
    """Reparte al azar los obstáculos del nivel, lejos del inicio del jugador y de las bases.

    level["obstacles"] dice cuántos hay de cada tipo, por ejemplo {"rock": 8, "mine": 4}.
    """
    spawn = cfg["spawn"]
    start = pygame.Vector2(level["player_start"]["x"], level["player_start"]["y"])
    bases = [pygame.Vector2(b["x"], b["y"]) for b in level["bases"]]
    for kind, count in level.get("obstacles", {}).items():
        for _ in range(count):
            pos = _free_position(start, bases, spawn, world_size)
            CREATORS[kind](world, pos, cfg[kind])


def _free_position(start: pygame.Vector2, bases: list[pygame.Vector2], spawn: dict,
                   world_size: pygame.Vector2) -> pygame.Vector2:
    """Posición al azar a distancia mínima del jugador y de las bases (en el mundo toroidal).

    Si no encuentra una en spawn["attempts"] intentos, devuelve la última probada.
    """
    pos = pygame.Vector2()
    for _ in range(spawn["attempts"]):
        pos = pygame.Vector2(random.uniform(0, world_size.x), random.uniform(0, world_size.y))
        far_from_player = wrap_delta(pos - start, world_size).length() >= spawn["min_distance_player"]
        far_from_bases = all(wrap_delta(pos - b, world_size).length() >= spawn["min_distance_base"]
                             for b in bases)
        if far_from_player and far_from_bases:
            return pos
    return pos
