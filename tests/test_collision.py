"""Pruebas de la detección de colisiones AABB con CHitBox (#16)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_collision import hitbox_rect, system_collision

WORLD = pygame.Vector2(1000, 800)


def make(world, center, size, offset=None, layer="", mask=()):
    return world.create_entity(CTransform(pygame.Vector2(center)),
                               CHitBox(pygame.Vector2(size), offset, layer, mask))


def pairs(world, world_size=None):
    return {frozenset(p) for p in system_collision(world, world_size)}


class CollisionTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def test_hitbox_centrada_en_la_posicion(self):
        e = make(self.w, (50, 40), (10, 6))
        rect = hitbox_rect(self.w.component_for_entity(e, CTransform),
                           self.w.component_for_entity(e, CHitBox))
        self.assertEqual((rect.centerx, rect.centery, rect.w, rect.h), (50, 40, 10, 6))

    def test_se_superponen_y_las_capas_chocan(self):
        player = make(self.w, (5, 5), (10, 10), layer="PLAYER", mask=("ENEMY",))
        enemy = make(self.w, (10, 10), (10, 10), layer="ENEMY")
        self.assertEqual(pairs(self.w), {frozenset((player, enemy))})

    def test_separadas_no_chocan(self):
        make(self.w, (5, 5), (10, 10), layer="PLAYER", mask=("ENEMY",))
        make(self.w, (25, 5), (10, 10), layer="ENEMY")
        self.assertEqual(pairs(self.w), set())

    def test_bordes_que_solo_se_tocan_no_chocan(self):
        make(self.w, (5, 5), (10, 10), layer="PLAYER", mask=("ENEMY",))
        make(self.w, (15, 5), (10, 10), layer="ENEMY")
        self.assertEqual(pairs(self.w), set())

    def test_offset_mueve_la_hitbox_independiente_del_sprite(self):
        # Mismo centro, pero la hitbox del jugador está corrida 10 px a la izquierda
        make(self.w, (20, 20), (4, 4), offset=(-10, 0), layer="PLAYER", mask=("ENEMY",))
        make(self.w, (20, 20), (4, 4), layer="ENEMY")
        self.assertEqual(pairs(self.w), set())

    def test_capas_fuera_de_las_mascaras_no_se_revisan(self):
        make(self.w, (5, 5), (10, 10), layer="ENEMY", mask=("PLAYER",))
        make(self.w, (8, 8), (10, 10), layer="ENEMY", mask=("PLAYER",))
        self.assertEqual(pairs(self.w), set())

    def test_basta_con_una_mascara(self):
        bullet = make(self.w, (1, 1), (2, 2), layer="PLAYER_BULLET", mask=("OBSTACLE",))
        rock = make(self.w, (4, 4), (8, 8), layer="OBSTACLE")
        self.assertEqual(pairs(self.w), {frozenset((bullet, rock))})


class ToroidalCollisionTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def test_chocan_a_traves_del_borde_horizontal(self):
        a = make(self.w, (2, 400), (10, 10), layer="PLAYER", mask=("ENEMY",))
        b = make(self.w, (996, 400), (10, 10), layer="ENEMY")
        self.assertEqual(pairs(self.w, WORLD), {frozenset((a, b))})

    def test_chocan_a_traves_del_borde_vertical(self):
        a = make(self.w, (500, 797), (10, 10), layer="PLAYER", mask=("ENEMY",))
        b = make(self.w, (500, 3), (10, 10), layer="ENEMY")
        self.assertEqual(pairs(self.w, WORLD), {frozenset((a, b))})

    def test_sin_world_size_no_hay_vuelta(self):
        make(self.w, (2, 400), (10, 10), layer="PLAYER", mask=("ENEMY",))
        make(self.w, (996, 400), (10, 10), layer="ENEMY")
        self.assertEqual(pairs(self.w), set())


if __name__ == "__main__":
    unittest.main()
