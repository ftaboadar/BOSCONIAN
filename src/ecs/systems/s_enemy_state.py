"""Patrón State de la IA enemiga: cada estado aplica un steering behaviour.

Máquina de estados por tipo de enemigo:
  I: CHASE --(chase_seconds)--> LEAVE   persigue y se va después de un rato
  P: CHASE --(chase_seconds)--> WANDER  persigue y pronto se vuelve aleatorio
  E: STRAIGHT                           va derecho, rápido, sin desviarse
"""

import random

import esper
import pygame

from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_steering import CSteering
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.engine import steering

# Estado con el que nace cada tipo y al que pasa cuando se le acaba la persecución.
INITIAL_STATE = {"I": EnemyState.CHASE, "P": EnemyState.CHASE, "E": EnemyState.STRAIGHT}
AFTER_CHASE = {"I": EnemyState.LEAVE, "P": EnemyState.WANDER}

_rng = random.Random()


def system_enemy_state(world: esper.World, player_pos: pygame.Vector2,
                       world_size: pygame.Vector2, delta_time: float,
                       rng: random.Random = _rng) -> None:
    for _, (c_t, c_v, c_state, c_steer) in world.get_components(
            CTransform, CVelocity, CEnemyState, CSteering):
        c_state.time_in_state += delta_time
        if c_state.state == EnemyState.CHASE:
            desired = _do_chase(c_t, c_state, c_steer, player_pos, world_size)
        elif c_state.state == EnemyState.LEAVE:
            desired = steering.flee(c_t.pos, player_pos, world_size)
        elif c_state.state == EnemyState.WANDER:
            desired = _do_wander(c_v, c_steer, delta_time, rng)
        else:  # STRAIGHT: no gira
            continue
        # Locomoción común: gira hacia la dirección deseada sin cambiar de rapidez.
        c_v.vel = steering.turn_towards(c_v.vel, desired, c_steer.turn_rate * delta_time)


def _change_state(c_state: CEnemyState, new_state: EnemyState) -> None:
    c_state.state = new_state
    c_state.time_in_state = 0.0


def _do_chase(c_t: CTransform, c_state: CEnemyState, c_steer: CSteering,
              player_pos: pygame.Vector2, world_size: pygame.Vector2) -> pygame.Vector2:
    if c_state.time_in_state >= c_state.chase_seconds:
        _change_state(c_state, AFTER_CHASE[c_state.kind])
    # Seek desviado: con menos dificultad el ángulo es mayor y le cuesta alcanzar al jugador.
    return steering.seek(c_t.pos, player_pos, world_size).rotate(c_steer.deviation)


def _do_wander(c_v: CVelocity, c_steer: CSteering, dt: float,
               rng: random.Random) -> pygame.Vector2:
    w = c_steer.wander
    c_steer.wander_angle += rng.uniform(-w["jitter"], w["jitter"]) * dt
    return steering.wander(c_v.vel, c_steer.wander_angle, w["distance"], w["radius"])
