"""Pruebas de las reglas de colisión y rebote entre entidades (#25)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_invulnerable import CInvulnerable
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.engine.data_loader import load_json

RULES = load_rules(load_json("assets/cfg/collisions.json"))
WORLD = pygame.Vector2(1000, 800)
PLAYER_MASK = ("ENEMY", "ENEMY_BULLET")
ENEMY_MASK = ("ENEMY", "BASE", "PLAYER")


def make(world, center, size, layer, mask=(), vel=None):
    ent = world.create_entity(CTransform(pygame.Vector2(center)),
                              CHitBox(pygame.Vector2(size), None, layer, mask))
    if vel is not None:
        world.add_component(ent, CVelocity(pygame.Vector2(vel)))
    return ent


def step(world, world_size=None):
    system_collision_rules(world, system_collision(world, world_size), RULES, world_size)
    system_destroy(world)


class BounceTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def pos(self, e):
        return self.w.component_for_entity(e, CTransform).pos

    def vel(self, e):
        return self.w.component_for_entity(e, CVelocity).vel

    def test_enemigos_rebotan_en_x(self):
        e1 = make(self.w, (5, 5), (10, 10), "ENEMY", ENEMY_MASK, vel=(30, 0))
        e2 = make(self.w, (13, 5), (10, 10), "ENEMY", ENEMY_MASK, vel=(-30, 0))
        step(self.w)
        self.assertLess(self.vel(e1).x, 0)
        self.assertGreater(self.vel(e2).x, 0)
        self.assertGreaterEqual(self.pos(e2).x - self.pos(e1).x, 10)
        self.assertEqual(system_collision(self.w), [])

    def test_enemigos_rebotan_en_y(self):
        e1 = make(self.w, (5, 5), (10, 10), "ENEMY", ENEMY_MASK, vel=(0, 20))
        e2 = make(self.w, (5, 12), (10, 10), "ENEMY", ENEMY_MASK, vel=(0, -20))
        step(self.w)
        self.assertLess(self.vel(e1).y, 0)
        self.assertGreater(self.vel(e2).y, 0)

    def test_enemigo_rebota_contra_base_fija(self):
        base = make(self.w, (35, 15), (30, 30), "BASE")
        enemy = make(self.w, (17, 15), (10, 10), "ENEMY", ENEMY_MASK, vel=(40, 0))
        step(self.w)
        self.assertEqual(self.pos(base), pygame.Vector2(35, 15))
        self.assertLess(self.vel(enemy).x, 0)
        self.assertLessEqual(self.pos(enemy).x + 5, 20)

    def test_enemigo_que_ya_se_aleja_no_se_invierte(self):
        make(self.w, (35, 15), (30, 30), "BASE")
        enemy = make(self.w, (17, 15), (10, 10), "ENEMY", ENEMY_MASK, vel=(-40, 0))
        step(self.w)
        self.assertEqual(self.vel(enemy).x, -40)

    def test_rebote_a_traves_del_borde_del_mundo(self):
        # e1 está a la izquierda del borde derecho, e2 justo después del borde (x pequeña)
        e1 = make(self.w, (996, 400), (10, 10), "ENEMY", ENEMY_MASK, vel=(30, 0))
        e2 = make(self.w, (3, 400), (10, 10), "ENEMY", ENEMY_MASK, vel=(-30, 0))
        step(self.w, WORLD)
        self.assertLess(self.vel(e1).x, 0)
        self.assertGreater(self.vel(e2).x, 0)
        self.assertEqual(system_collision(self.w, WORLD), [])


class DestroyTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def test_enemigo_contra_jugador_mueren_ambos(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK)
        enemy = make(self.w, (10, 10), (10, 10), "ENEMY", ENEMY_MASK)
        step(self.w)
        self.assertFalse(self.w.entity_exists(player))
        self.assertFalse(self.w.entity_exists(enemy))

    def test_bala_enemiga_contra_jugador_mueren_ambos(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK)
        bullet = make(self.w, (5, 5), (2, 2), "ENEMY_BULLET")
        step(self.w)
        self.assertFalse(self.w.entity_exists(player))
        self.assertFalse(self.w.entity_exists(bullet))

    def test_choque_multiple_en_un_frame(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK)
        make(self.w, (10, 5), (10, 10), "ENEMY", ENEMY_MASK)
        make(self.w, (10, 10), (10, 10), "ENEMY", ENEMY_MASK)
        step(self.w)
        self.assertFalse(self.w.entity_exists(player))

    def test_jugador_contra_base_solo_muere_el_jugador(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK + ("BASE",))
        base = make(self.w, (10, 10), (24, 24), "BASE")
        step(self.w)
        self.assertFalse(self.w.entity_exists(player))
        self.assertTrue(self.w.entity_exists(base))

    def test_invulnerable_no_recibe_destroy_pero_el_otro_si(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK)
        self.w.add_component(player, CInvulnerable())
        enemy = make(self.w, (10, 10), (10, 10), "ENEMY", ENEMY_MASK)
        step(self.w)
        self.assertTrue(self.w.entity_exists(player))
        self.assertIsNone(self.w.try_component(player, CDestroy))
        self.assertFalse(self.w.entity_exists(enemy))

    def test_bala_enemiga_no_destruye_al_invulnerable(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK)
        self.w.add_component(player, CInvulnerable())
        bullet = make(self.w, (5, 5), (2, 2), "ENEMY_BULLET")
        step(self.w)
        self.assertTrue(self.w.entity_exists(player))
        self.assertFalse(self.w.entity_exists(bullet))

    def test_invulnerable_contra_base_no_muere(self):
        player = make(self.w, (5, 5), (10, 10), "PLAYER", PLAYER_MASK + ("BASE",))
        self.w.add_component(player, CInvulnerable())
        make(self.w, (10, 10), (24, 24), "BASE")
        step(self.w)
        self.assertTrue(self.w.entity_exists(player))

    def test_pares_sin_regla_se_ignoran(self):
        a = make(self.w, (5, 5), (10, 10), "PLAYER_BULLET", ("ENEMY",))
        b = make(self.w, (10, 10), (10, 10), "ENEMY")
        step(self.w)
        self.assertTrue(self.w.entity_exists(a))
        self.assertTrue(self.w.entity_exists(b))
        self.assertIsNone(self.w.try_component(a, CDestroy))


if __name__ == "__main__":
    unittest.main()
