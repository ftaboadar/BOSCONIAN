"""Pruebas de la detección de colisiones AABB con CHitBox (#16)."""

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_collision import system_collision


def make(world, pos, size, offset=None, layer="", mask=()):
    return world.create_entity(CTransform(pygame.Vector2(pos)),
                               CHitBox(pygame.Vector2(size), offset, layer, mask))


def pairs(world):
    return {frozenset(p) for p in system_collision(world)}


# Se superponen y las capas chocan entre sí
world = esper.World()
player = make(world, (0, 0), (10, 10), layer="PLAYER", mask=("ENEMY",))
enemy = make(world, (5, 5), (10, 10), layer="ENEMY")
assert pairs(world) == {frozenset((player, enemy))}

# Separados: no hay colisión
world = esper.World()
make(world, (0, 0), (10, 10), layer="PLAYER", mask=("ENEMY",))
make(world, (20, 0), (10, 10), layer="ENEMY")
assert pairs(world) == set()

# Bordes que solo se tocan no cuentan como colisión
world = esper.World()
make(world, (0, 0), (10, 10), layer="PLAYER", mask=("ENEMY",))
make(world, (10, 0), (10, 10), layer="ENEMY")
assert pairs(world) == set()

# La hitbox es independiente del sprite: con offset ya no se tocan
world = esper.World()
make(world, (0, 0), (4, 4), offset=(3, 3), layer="PLAYER", mask=("ENEMY",))
make(world, (8, 0), (4, 4), layer="ENEMY")
assert pairs(world) == set()

# Capas que no están en ninguna máscara no se revisan
world = esper.World()
make(world, (0, 0), (10, 10), layer="ENEMY", mask=("PLAYER",))
make(world, (5, 5), (10, 10), layer="ENEMY", mask=("PLAYER",))
assert pairs(world) == set()

# Basta con que una de las dos entidades incluya a la otra en su máscara
world = esper.World()
bullet = make(world, (0, 0), (2, 2), layer="PLAYER_BULLET", mask=("OBSTACLE",))
rock = make(world, (1, 1), (8, 8), layer="OBSTACLE")
assert pairs(world) == {frozenset((bullet, rock))}

print("COLLISION OK")
