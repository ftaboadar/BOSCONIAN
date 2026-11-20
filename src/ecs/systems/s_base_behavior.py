"""Comportamiento de las bases: las torretas disparan al jugador cuando está cerca y el
núcleo se abre y se cierra, lanzando un enemigo E cada vez que se abre."""

import esper
import pygame

from src.create.prefab_creator import create_enemy, create_enemy_bullet
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_core import CBaseCore
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret
from src.ecs.systems.s_base_damage import draw_base_part, draw_turret
from src.engine.camera import wrap_delta
from src.engine.sfx import play_sound

TURRET_CLOSED, TURRET_OPEN, TURRET_WARN = 0, 1, 2


def system_turrets(world: esper.World, player_pos: pygame.Vector2, world_size: pygame.Vector2,
                   cfg: dict, delta_time: float) -> None:
    """Con el jugador a menos de `turret.range` px y de su lado de la base, la torreta se
    abre y le dispara una bala cada vez que cumple su intervalo; `warn_seconds` antes se ve
    a punto de disparar. Si no, se cierra y su cuenta queda en pausa.

    Solo dispara hacia afuera: una bala nunca cruza la base ni alcanza al enemigo E que
    sale del núcleo."""
    turret = cfg["turret"]
    for _, (c_t, c_part, c_tur) in world.get_components(CTransform, CBasePart, CTurret):
        to_player = wrap_delta(player_pos - c_t.pos, world_size)
        frame = TURRET_CLOSED
        if to_player.length() <= turret["range"] and to_player.dot(c_part.offset) >= 0:
            c_tur.timer += delta_time
            if c_tur.timer >= c_tur.interval and to_player.length_squared() > 0:
                c_tur.timer = 0.0  # un disparo por intervalo, aunque el frame haya sido largo
                create_enemy_bullet(world, c_t.pos,
                                    to_player.normalize() * cfg["bullet"]["speed"], cfg["bullet"])
                play_sound("enemy_shoot")
            warn = c_tur.timer >= c_tur.interval - turret["warn_seconds"]
            frame = TURRET_WARN if warn else TURRET_OPEN
        if frame != c_tur.frame:
            c_tur.frame = frame
            draw_turret(world.component_for_entity(c_part.base, CSurface).surf, c_part.offset,
                        c_tur.frames, frame)


def system_base_cores(world: esper.World, player_pos: pygame.Vector2,
                      world_size: pygame.Vector2, cfg_enemies: dict, player_speed: float,
                      delta_time: float) -> None:
    """Avanza el ciclo de los núcleos que se abren y cierran. Al quedar abierto, el núcleo
    lanza un enemigo E por la abertura de la base que da hacia el jugador."""
    for _, (c_t, c_part, c_core) in world.get_components(CTransform, CBasePart, CBaseCore):
        c_base = world.component_for_entity(c_part.base, CBase)
        c_core.timer += delta_time
        frame = _core_frame(c_core, len(c_base.core_frames))
        if frame == c_core.frame:
            continue
        c_core.frame = frame
        draw_base_part(world.component_for_entity(c_part.base, CSurface).surf, c_part.offset,
                       c_base.core_frames[frame], c_base.core_radius)
        if frame == len(c_base.core_frames) - 1:
            to_player = wrap_delta(player_pos - c_t.pos, world_size)
            if c_base.orientation == "vertical":
                direction = pygame.Vector2(0, 1 if to_player.y >= 0 else -1)
            else:
                direction = pygame.Vector2(1 if to_player.x >= 0 else -1, 0)
            # El E va derecho: la dificultad (desviación al perseguir) no le afecta.
            create_enemy(world, "E", c_t.pos, direction, cfg_enemies, player_speed, 0.0)


def _core_frame(c_core: CBaseCore, n_frames: int) -> int:
    """Cuadro (0 cerrado ... n_frames - 1 abierto) que toca según el tiempo del ciclo:
    cerrado, abriéndose por los cuadros intermedios, abierto y cerrándose."""
    steps = n_frames - 2  # cuadros intermedios
    moving = steps * c_core.frame_seconds
    t = c_core.timer % (c_core.closed_seconds + c_core.open_seconds + 2 * moving)
    if t < c_core.closed_seconds:
        return 0
    t -= c_core.closed_seconds
    if t < moving:
        return 1 + min(int(t / c_core.frame_seconds), steps - 1)
    t -= moving
    if t < c_core.open_seconds:
        return n_frames - 1
    t -= c_core.open_seconds
    return steps - min(int(t / c_core.frame_seconds), steps - 1)
