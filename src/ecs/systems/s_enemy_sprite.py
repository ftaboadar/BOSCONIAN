"""Sprite de los enemigos: mira hacia donde se mueve, en pasos de 45 grados."""

import math

import esper
import pygame

from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_player_ship import CHeadingSprites
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_velocity import CVelocity

# Rumbo (dx, dy) para cada octante, empezando por arriba y avanzando en sentido horario.
OCTANTS = ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1))


def heading_key(vel: pygame.Vector2) -> tuple[int, int]:
    """La dirección de las 8 posibles más cercana a `vel` (con arriba = (0, -1)).

    Una velocidad nula mira hacia arriba."""
    if vel.length_squared() == 0:
        return OCTANTS[0]
    angle = math.degrees(math.atan2(vel.x, -vel.y))  # 0 = arriba, positivo = horario
    return OCTANTS[round(angle / 45) % 8]


def system_enemy_sprite(world: esper.World) -> None:
    """Muestra el sprite que corresponde a la dirección actual de cada enemigo.

    Un enemigo detenido conserva el último que tenía."""
    for _, (_c_e, c_v, c_h, c_s) in world.get_components(
            CEnemyState, CVelocity, CHeadingSprites, CSurface):
        if c_v.vel.length_squared() > 0:
            c_s.surf = c_h.surfaces[heading_key(c_v.vel)]
