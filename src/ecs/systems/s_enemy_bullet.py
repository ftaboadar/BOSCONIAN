"""Balas de las torretas: caducan y destruyen al enemigo con el que chocan."""

import esper
import pygame

from src.ecs.components.c_enemy_bullet import CEnemyBullet
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.engine.camera import wrap_delta


def system_enemy_bullets(world: esper.World, world_size: pygame.Vector2,
                         delta_time: float) -> None:
    """Quita las balas que cumplieron su tiempo. Las demás chocan (AABB del tamaño del
    sprite, por el camino corto del mundo toroidal) con los enemigos: mueren la bala y
    el enemigo.

    Provisional: cuando lleguen el componente HitBox y las reglas de colisión (#16, #25)
    este choque pasa a ser una regla más.
    """
    enemies = [(ent, c_t.pos, c_s.surf.get_size()) for ent, (c_t, c_s, _c_e)
               in world.get_components(CTransform, CSurface, CEnemyState)]
    dead: set[int] = set()
    for bullet, (c_t, c_s, c_b) in world.get_components(CTransform, CSurface, CEnemyBullet):
        c_b.seconds_left -= delta_time
        if c_b.seconds_left <= 0:
            dead.add(bullet)
            continue
        w, h = c_s.surf.get_size()
        for enemy, pos, (enemy_w, enemy_h) in enemies:
            d = wrap_delta(c_t.pos - pos, world_size)
            if enemy not in dead and abs(d.x) < (w + enemy_w) / 2 and abs(d.y) < (h + enemy_h) / 2:
                dead.update((bullet, enemy))
                break
    for ent in dead:
        world.delete_entity(ent, immediate=True)
