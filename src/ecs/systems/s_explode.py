import random

import esper
import pygame

from src.create.prefab_creator import create_explosion
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.engine.sfx import play_sound


def system_explode(world: esper.World, explosions_cfg: dict) -> None:
    """Crea la explosión de cada entidad explosiva que va a ser destruida.

    Debe correr antes de system_destroy, mientras la entidad todavía existe.
    Un tipo con "frames" es una explosión simple que conserva la velocidad.
    Un tipo con "count" es un grupo de explosiones repartidas en un radio.
    Si el tipo tiene "sound", suena una vez al explotar.
    """
    for ent, (_c_d, c_e, c_t) in world.get_components(CDestroy, CExplosive, CTransform):
        c_v = world.try_component(ent, CVelocity)
        vel = c_v.vel if c_v is not None else pygame.Vector2()
        cfg = explosions_cfg[c_e.kind]
        if "sound" in cfg:  # una vez por entidad, aunque el grupo cree varias explosiones
            play_sound(cfg["sound"])
        if "frames" in cfg:
            create_explosion(world, c_t.pos, vel, cfg)
        else:
            create_explosion_group(world, c_t.pos, vel, cfg, explosions_cfg)


def create_explosion_group(world: esper.World, pos: pygame.Vector2, vel: pygame.Vector2,
                           cfg: dict, explosions_cfg: dict) -> None:
    """Grupo de explosiones simples repartidas al azar en un radio alrededor de `pos`."""
    single = explosions_cfg[cfg["explosion"]]
    group_vel = vel if cfg.get("keep_velocity", False) else pygame.Vector2()
    for _ in range(cfg["count"]):
        offset = pygame.Vector2(random.uniform(0, cfg["radius"]), 0).rotate(random.uniform(0, 360))
        create_explosion(world, pos + offset, group_vel, single)
