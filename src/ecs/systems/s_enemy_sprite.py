"""Sprite de los enemigos: mira hacia donde se mueve, en pasos iguales (16 como el original)."""

import math

import esper
import pygame

from src.ecs.components.c_angle_sprites import CAngleSprites
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_velocity import CVelocity


def heading_index(vel: pygame.Vector2, steps: int) -> int:
    """Paso de giro (0..steps-1, horario desde arriba) más cercano a la dirección de `vel`.

    Una velocidad nula mira hacia arriba."""
    if vel.length_squared() == 0:
        return 0
    angle = math.degrees(math.atan2(vel.x, -vel.y))  # 0 = arriba, positivo = horario
    return round(angle / (360 / steps)) % steps


def system_enemy_sprite(world: esper.World) -> None:
    """Muestra el sprite que corresponde a la dirección actual de cada enemigo.

    Un enemigo detenido conserva el último que tenía."""
    for _, (_c_e, c_v, c_a, c_s) in world.get_components(
            CEnemyState, CVelocity, CAngleSprites, CSurface):
        if c_v.vel.length_squared() > 0:
            c_s.surf = c_a.surfaces[heading_index(c_v.vel, len(c_a.surfaces))]
