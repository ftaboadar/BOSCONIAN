"""Steering behaviours (Reynolds) para un vehículo de velocidad constante.

Cada comportamiento devuelve la dirección deseada; `turn_towards` es la locomoción:
gira el rumbo hacia esa dirección con un límite de grados por segundo.
"""

import pygame

from src.engine.camera import wrap_delta


def seek(pos: pygame.Vector2, target: pygame.Vector2,
         world_size: pygame.Vector2) -> pygame.Vector2:
    """Dirección hacia el objetivo por el camino más corto del mundo toroidal."""
    return wrap_delta(target - pos, world_size)


def flee(pos: pygame.Vector2, threat: pygame.Vector2,
         world_size: pygame.Vector2) -> pygame.Vector2:
    """Dirección contraria a la amenaza."""
    return -seek(pos, threat, world_size)


def wander(heading: pygame.Vector2, wander_angle: float,
           distance: float, radius: float) -> pygame.Vector2:
    """Dirección hacia un punto de un círculo proyectado `distance` px por delante.

    `wander_angle` se mide respecto al rumbo; variarlo poco a poco (random walk)
    produce giros suaves al azar.
    """
    if heading.length_squared() == 0:
        return pygame.Vector2()
    forward = heading.normalize()
    return forward * distance + forward.rotate(wander_angle) * radius


def turn_towards(heading: pygame.Vector2, desired: pygame.Vector2,
                 max_degrees: float) -> pygame.Vector2:
    """Rota `heading` hacia `desired` sin pasar de `max_degrees`; conserva la magnitud."""
    if desired.length_squared() == 0:
        return pygame.Vector2(heading)
    angle = heading.angle_to(desired)
    angle = (angle + 180) % 360 - 180  # el giro más corto, en [-180, 180)
    return heading.rotate(max(-max_degrees, min(max_degrees, angle)))
