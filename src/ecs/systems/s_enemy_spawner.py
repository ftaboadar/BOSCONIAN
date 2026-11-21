"""Spawn de enemigos I, P y E: salen al azar alrededor del jugador, fuera de la pantalla."""

import random

import esper
import pygame

from src.create.prefab_creator import create_enemy
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_transform import CTransform
from src.engine.camera import wrap_delta

_rng = random.Random()


def system_enemy_spawner(world: esper.World, player_pos: pygame.Vector2,
                         world_size: pygame.Vector2, cfg: dict, player_speed: float,
                         delta_time: float, rng: random.Random = _rng) -> None:
    """Cada intervalo crea un enemigo de tipo al azar, en una dirección al azar, a
    `spawn.distance` px del jugador y apuntando hacia él. Respeta el tope de vivos."""
    kinds = list(cfg["types"])
    weights = [cfg["types"][k]["spawn_weight"] for k in kinds]
    for _, c_sp in world.get_component(CEnemySpawner):
        c_sp.timer += delta_time
        if c_sp.timer < c_sp.interval:
            continue
        c_sp.timer -= c_sp.interval
        if len(world.get_component(CEnemyState)) >= c_sp.max_alive:
            continue
        offset = pygame.Vector2(cfg["spawn"]["distance"], 0).rotate(rng.uniform(0, 360))
        pos = player_pos + offset
        pos = pygame.Vector2(pos.x % world_size.x, pos.y % world_size.y)
        create_enemy(world, rng.choices(kinds, weights)[0], pos, -offset,
                     cfg, player_speed, c_sp.difficulty, rng)


def system_enemy_despawn(world: esper.World, player_pos: pygame.Vector2,
                         world_size: pygame.Vector2, max_distance: float) -> None:
    """Quita los enemigos que se alejaron del jugador más de `max_distance` px."""
    gone = [ent for ent, (c_t, _c_s) in world.get_components(CTransform, CEnemyState)
            if wrap_delta(c_t.pos - player_pos, world_size).length() > max_distance]
    for ent in gone:
        world.delete_entity(ent, immediate=True)
