import esper
import pygame

from src.ecs.components.c_player_ship import CHeadingSprites, CPlayerShip
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_weapon import CWeapon
from src.engine.input.command import Phase

HEADING_KEYS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}


def heading_from_held(held: set[str], current: tuple[int, int]) -> tuple[int, int]:
    """Dirección que piden las teclas; opuestas se anulan y sin teclas se conserva la actual."""
    dx = sum(v[0] for k, v in HEADING_KEYS.items() if k in held)
    dy = sum(v[1] for k, v in HEADING_KEYS.items() if k in held)
    return (dx, dy) if (dx, dy) != (0, 0) else current


def system_player_input(world: esper.World, action: str, phase: Phase,
                        can_steer: bool, can_fire: bool) -> None:
    """Lleva una acción del input a la nave: las direcciones presionadas y el disparo.

    Soltar una tecla siempre se registra (también en pausa), para que no quede una tecla
    fantasma. Sin `can_steer` (BLAST OFF!) no se guarda la dirección; sin `can_fire` (pausa
    o BLAST OFF!) FIRE queda presionada pero no deja un disparo pendiente."""
    for _, (c_p, c_w) in world.get_components(CPlayerShip, CWeapon):
        if action in HEADING_KEYS:
            if phase != Phase.START:
                c_p.held.discard(action)
            elif can_steer:
                c_p.held.add(action)
        elif action == "FIRE":
            c_w.held = phase == Phase.START
            if c_w.held and can_fire:
                c_w.trigger = True


def system_player_movement(world: esper.World, delta_time: float) -> None:
    """La nave nunca se detiene: gira al instante, conserva su rapidez y acelera hasta el máximo."""
    for _, (c_p, c_v) in world.get_components(CPlayerShip, CVelocity):
        c_p.heading = heading_from_held(c_p.held, c_p.heading)
        c_p.speed = min(c_p.max_speed, c_p.speed + c_p.acceleration * delta_time)
        c_v.vel = pygame.Vector2(c_p.heading).normalize() * c_p.speed


def system_player_sprite(world: esper.World) -> None:
    """Muestra el sprite que corresponde a la dirección actual."""
    for _, (c_p, c_h, c_s) in world.get_components(CPlayerShip, CHeadingSprites, CSurface):
        c_s.surf = c_h.surfaces[c_p.heading]
