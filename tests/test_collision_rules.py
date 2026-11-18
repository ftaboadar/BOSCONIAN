"""Pruebas de las reglas de colisión y rebote entre entidades (#25)."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.engine.data_loader import load_json

RULES = load_rules(load_json("assets/cfg/collisions.json"))

PLAYER_MASK = ("ENEMY", "ENEMY_BULLET")
ENEMY_MASK = ("ENEMY", "BASE", "PLAYER")


def make(world, pos, size, layer, mask=(), vel=None):
    ent = world.create_entity(CTransform(pygame.Vector2(pos)),
                              CHitBox(pygame.Vector2(size), None, layer, mask))
    if vel is not None:
        world.add_component(ent, CVelocity(pygame.Vector2(vel)))
    return ent


def step(world):
    system_collision_rules(world, system_collision(world), RULES)
    system_destroy(world)


def pos(world, ent):
    return world.component_for_entity(ent, CTransform).pos


def vel(world, ent):
    return world.component_for_entity(ent, CVelocity).vel


# Dos enemigos que se acercan en X rebotan: se separan y se invierten sus velocidades
world = esper.World()
e1 = make(world, (0, 0), (10, 10), "ENEMY", ENEMY_MASK, vel=(30, 0))
e2 = make(world, (8, 0), (10, 10), "ENEMY", ENEMY_MASK, vel=(-30, 0))
step(world)
assert vel(world, e1).x < 0 and vel(world, e2).x > 0, (vel(world, e1), vel(world, e2))
assert pos(world, e1).x + 10 <= pos(world, e2).x, (pos(world, e1), pos(world, e2))
assert system_collision(world) == []

# Rebote en Y entre enemigos
world = esper.World()
e1 = make(world, (0, 0), (10, 10), "ENEMY", ENEMY_MASK, vel=(0, 20))
e2 = make(world, (0, 7), (10, 10), "ENEMY", ENEMY_MASK, vel=(0, -20))
step(world)
assert vel(world, e1).y < 0 and vel(world, e2).y > 0

# Enemigo contra base: solo el enemigo se mueve y rebota, la base queda fija
world = esper.World()
base = make(world, (20, 0), (30, 30), "BASE")
enemy = make(world, (12, 10), (10, 10), "ENEMY", ENEMY_MASK, vel=(40, 0))
step(world)
assert pos(world, base) == pygame.Vector2(20, 0)
assert vel(world, enemy).x < 0
assert pos(world, enemy).x + 10 <= 20

# Un enemigo que ya se aleja no se invierte (no queda "pegado")
world = esper.World()
base = make(world, (20, 0), (30, 30), "BASE")
enemy = make(world, (12, 10), (10, 10), "ENEMY", ENEMY_MASK, vel=(-40, 0))
step(world)
assert vel(world, enemy).x == -40

# Enemigo contra jugador: mueren ambos
world = esper.World()
player = make(world, (0, 0), (10, 10), "PLAYER", PLAYER_MASK)
enemy = make(world, (5, 5), (10, 10), "ENEMY", ENEMY_MASK)
step(world)
assert not world.entity_exists(player) and not world.entity_exists(enemy)

# Bala enemiga contra jugador: mueren ambos
world = esper.World()
player = make(world, (0, 0), (10, 10), "PLAYER", PLAYER_MASK)
bullet = make(world, (4, 4), (2, 2), "ENEMY_BULLET")
step(world)
assert not world.entity_exists(player) and not world.entity_exists(bullet)

# Un enemigo que toca a dos cosas en el mismo frame no rompe nada
world = esper.World()
player = make(world, (0, 0), (10, 10), "PLAYER", PLAYER_MASK)
e1 = make(world, (5, 0), (10, 10), "ENEMY", ENEMY_MASK)
e2 = make(world, (5, 5), (10, 10), "ENEMY", ENEMY_MASK)
step(world)
assert not world.entity_exists(player)

# Pares sin regla se ignoran
world = esper.World()
a = make(world, (0, 0), (10, 10), "PLAYER", ("BASE",))
b = make(world, (5, 5), (10, 10), "BASE")
step(world)
assert world.entity_exists(a) and world.entity_exists(b)
assert world.try_component(a, CDestroy) is None

print("COLLISION RULES OK")
