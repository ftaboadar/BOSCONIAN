import esper
import pygame

from src.create.prefab_creator import create_player_bullet
from src.ecs.components.c_player_bullet import CPlayerBullet
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_weapon import CWeapon
from src.engine.camera import Camera, wrap_delta


def system_player_fire(world: esper.World, delta_time: float) -> None:
    """Con FIRE (o manteniéndola) sale una bala hacia adelante y otra hacia atrás, respetando el enfriamiento."""
    for _, (c_p, c_t, c_w) in world.get_components(CPlayerShip, CTransform, CWeapon):
        c_w.timer = max(0.0, c_w.timer - delta_time)
        if not (c_w.held or c_w.trigger) or c_w.timer > 0:
            continue  # una pulsación pendiente espera al enfriamiento en vez de perderse
        c_w.trigger = False
        c_w.timer = c_w.cooldown
        forward = pygame.Vector2(c_p.heading).normalize()
        for direction, key in ((forward, c_p.heading), (-forward, (-c_p.heading[0], -c_p.heading[1]))):
            create_player_bullet(world, c_t.pos + direction * c_w.muzzle_offset,
                                 direction * c_w.bullet_speed, c_w.sprites[key])


def bullet_offscreen(delta: pygame.Vector2, viewport: pygame.Rect, margin: float) -> bool:
    """`delta` es la posición de la bala respecto al centro de la cámara."""
    return abs(delta.x) > viewport.w / 2 + margin or abs(delta.y) > viewport.h / 2 + margin


def system_bullet_cleanup(world: esper.World, camera: Camera, margin: float) -> None:
    """Las balas amigas se destruyen al salir de la pantalla (no dan la vuelta al mundo)."""
    for ent, (c_t, _c_b) in world.get_components(CTransform, CPlayerBullet):
        delta = wrap_delta(c_t.pos - camera.pos, camera.world_size)
        if bullet_offscreen(delta, camera.viewport, margin):
            world.delete_entity(ent, immediate=True)
