"""Pruebas de los obstáculos: rocas, minas y rocas indestructibles (#24)."""

import json
import os
import sys
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_obstacles import (create_mine, create_obstacles, create_rock,
                                         create_solid_rock)
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_explode import system_explode
from src.engine import data_loader
from src.engine.camera import wrap_delta
from src.engine.data_loader import ConfigError, load_json
from src.engine.game_engine import GameEngine

ENGINE = GameEngine()  # inicializa pygame, la ventana y los servicios
CFG = load_json("assets/cfg/obstacles.json")
EXPLOSIONS = load_json("assets/cfg/explosions.json")
RULES = load_rules(load_json("assets/cfg/collisions.json"))
WORLD = pygame.Vector2(1024, 1024)


def make(world, pos, layer, mask=(), size=(10, 10), vel=None):
    ent = world.create_entity(CTransform(pygame.Vector2(pos)),
                              CHitBox(pygame.Vector2(size), None, layer, mask))
    if vel is not None:
        world.add_component(ent, CVelocity(pygame.Vector2(vel)))
    return ent


def step(world, dt=1 / 60):
    """Un frame del ciclo de la escena: colisiones, reglas, explosiones, animación y borrado."""
    points = system_collision_rules(world, system_collision(world, WORLD), RULES, WORLD)
    system_explode(world, EXPLOSIONS)
    system_animation(world, dt)
    system_destroy(world)
    return points


def kind_of(world, ent):
    return world.component_for_entity(ent, CHitBox).layer


class PrefabTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def test_roca_estatica_con_puntos(self):
        r = create_rock(self.w, pygame.Vector2(10, 10), CFG["rock"])
        self.assertIsNone(self.w.try_component(r, CVelocity))
        self.assertEqual(self.w.component_for_entity(r, CPoints).points, CFG["rock"]["points"])
        self.assertEqual(kind_of(self.w, r), "ROCK")

    def test_mina_animada_en_bucle_con_puntos(self):
        m = create_mine(self.w, pygame.Vector2(10, 10), CFG["mine"])
        self.assertTrue(self.w.component_for_entity(m, CAnimation).loop)
        self.assertEqual(self.w.component_for_entity(m, CPoints).points, CFG["mine"]["points"])

    def test_roca_indestructible_se_mueve_a_su_velocidad(self):
        r = create_solid_rock(self.w, pygame.Vector2(10, 10), CFG["solid_rock"])
        vel = self.w.component_for_entity(r, CVelocity).vel
        self.assertAlmostEqual(vel.length(), CFG["solid_rock"]["speed"], places=4)


class SpawnTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()
        self.level = {"player_start": {"x": 512, "y": 512},
                      "bases": [{"x": 300, "y": 400}, {"x": 20, "y": 1010}],
                      "obstacles": {"rock": 12, "mine": 5, "solid_rock": 3}}

    def test_crea_la_cantidad_de_cada_tipo(self):
        create_obstacles(self.w, self.level, CFG, WORLD)
        layers = [hb.layer for _, hb in self.w.get_component(CHitBox)]
        self.assertEqual(layers.count("ROCK"), 12)
        self.assertEqual(layers.count("MINE"), 5)
        self.assertEqual(layers.count("ROCK_SOLID"), 3)

    def test_lejos_del_jugador_y_de_las_bases_en_el_mundo_toroidal(self):
        create_obstacles(self.w, self.level, CFG, WORLD)
        start = pygame.Vector2(512, 512)
        bases = [pygame.Vector2(300, 400), pygame.Vector2(20, 1010)]
        for _, (c_t, _hb) in self.w.get_components(CTransform, CHitBox):
            self.assertGreaterEqual(wrap_delta(c_t.pos - start, WORLD).length(),
                                    CFG["spawn"]["min_distance_player"])
            for b in bases:
                self.assertGreaterEqual(wrap_delta(c_t.pos - b, WORLD).length(),
                                        CFG["spawn"]["min_distance_base"])

    def test_nivel_sin_obstaculos(self):
        self.level.pop("obstacles")
        create_obstacles(self.w, self.level, CFG, WORLD)
        self.assertEqual(list(self.w.get_component(CHitBox)), [])


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def test_bala_destruye_roca_y_suma_sus_puntos(self):
        rock = create_rock(self.w, pygame.Vector2(100, 100), CFG["rock"])
        bullet = make(self.w, (100, 100), "PLAYER_BULLET", ("ROCK",), (2, 2))
        self.assertEqual(step(self.w), CFG["rock"]["points"])
        self.assertFalse(self.w.entity_exists(rock))
        self.assertFalse(self.w.entity_exists(bullet))

    def test_dos_balas_en_el_mismo_frame_puntuan_una_vez(self):
        create_rock(self.w, pygame.Vector2(100, 100), CFG["rock"])
        make(self.w, (99, 100), "PLAYER_BULLET", ("ROCK",), (2, 2))
        make(self.w, (101, 100), "PLAYER_BULLET", ("ROCK",), (2, 2))
        self.assertEqual(step(self.w), CFG["rock"]["points"])

    def test_bala_destruye_mina_y_suma_sus_puntos(self):
        create_mine(self.w, pygame.Vector2(100, 100), CFG["mine"])
        make(self.w, (100, 100), "PLAYER_BULLET", ("MINE",), (2, 2))
        self.assertEqual(step(self.w), CFG["mine"]["points"])

    def test_chocar_con_roca_no_da_puntos(self):
        create_rock(self.w, pygame.Vector2(100, 100), CFG["rock"])
        player = make(self.w, (100, 100), "PLAYER", ("ROCK",))
        self.assertEqual(step(self.w), 0)
        self.assertFalse(self.w.entity_exists(player))

    def test_enemigo_muere_al_chocar_con_roca(self):
        create_rock(self.w, pygame.Vector2(100, 100), CFG["rock"])
        enemy = make(self.w, (100, 100), "ENEMY", ("ROCK",))
        step(self.w)
        self.assertFalse(self.w.entity_exists(enemy))

    def test_explosion_de_mina_es_letal_y_de_otro_color(self):
        mine = create_mine(self.w, pygame.Vector2(100, 100), CFG["mine"])
        make(self.w, (100, 100), "PLAYER_BULLET", ("MINE",), (2, 2))
        step(self.w)
        self.assertFalse(self.w.entity_exists(mine))
        blasts = [e for e, hb in self.w.get_component(CHitBox) if hb.layer == "MINE_BLAST"]
        self.assertEqual(len(blasts), 1)
        self.assertNotEqual(EXPLOSIONS["mine"]["frames"], EXPLOSIONS["simple"]["frames"])
        # Un jugador que entra a la explosión muere
        player = make(self.w, (104, 100), "PLAYER", ("MINE_BLAST",))
        step(self.w)
        self.assertFalse(self.w.entity_exists(player))

    def test_explosion_de_mina_desaparece_al_terminar(self):
        create_mine(self.w, pygame.Vector2(100, 100), CFG["mine"])
        make(self.w, (100, 100), "PLAYER_BULLET", ("MINE",), (2, 2))
        for _ in range(120):
            step(self.w)
        self.assertEqual([e for e, hb in self.w.get_component(CHitBox)
                          if hb.layer == "MINE_BLAST"], [])

    def test_roca_indestructible_sobrevive_y_mata(self):
        solid = create_solid_rock(self.w, pygame.Vector2(100, 100), CFG["solid_rock"])
        bullet = make(self.w, (100, 100), "PLAYER_BULLET", ("ROCK_SOLID",), (2, 2))
        enemy_bullet = make(self.w, (102, 100), "ENEMY_BULLET", ("ROCK_SOLID",), (2, 2))
        player = make(self.w, (98, 100), "PLAYER", ("ROCK_SOLID",))
        enemy = make(self.w, (100, 102), "ENEMY", ("ROCK_SOLID",))
        self.assertEqual(step(self.w), 0)
        self.assertTrue(self.w.entity_exists(solid))
        for e in (bullet, enemy_bullet, player, enemy):
            self.assertFalse(self.w.entity_exists(e))

    def test_roca_indestructible_rebota_en_base(self):
        base = make(self.w, (130, 100), "BASE", (), (24, 24))
        solid = create_solid_rock(self.w, pygame.Vector2(114, 100), CFG["solid_rock"])
        self.w.component_for_entity(solid, CVelocity).vel = pygame.Vector2(30, 0)
        step(self.w)
        self.assertLess(self.w.component_for_entity(solid, CVelocity).vel.x, 0)
        self.assertEqual(self.w.component_for_entity(base, CTransform).pos, pygame.Vector2(130, 100))


class LevelTests(unittest.TestCase):
    def test_el_nivel_1_define_obstaculos(self):
        level = data_loader.load_level(1)
        self.assertGreater(sum(level["obstacles"].values()), 0)

    def _load_with(self, obstacles):
        level = {"round": 1, "player_start": {"x": 0, "y": 0}, "bases": [],
                 "obstacles": obstacles}
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "level_01.json"), "w", encoding="utf-8") as f:
                json.dump(level, f)
            old = data_loader.LEVELS_DIR
            data_loader.LEVELS_DIR = tmp
            try:
                return data_loader.load_level(1)
            finally:
                data_loader.LEVELS_DIR = old

    def test_tipo_desconocido_es_error(self):
        with self.assertRaises(ConfigError):
            self._load_with({"asteroide": 3})

    def test_cantidad_negativa_es_error(self):
        with self.assertRaises(ConfigError):
            self._load_with({"rock": -1})


class SceneTests(unittest.TestCase):
    def setUp(self):
        ENGINE.state.score = 0
        ENGINE._next_scene = None
        ENGINE._apply_scene_change("PLAY")
        self.scene = ENGINE._current_scene
        self.scene.blast_left = 0

    def test_el_nivel_crea_sus_obstaculos(self):
        layers = [hb.layer for _, hb in self.scene.world.get_component(CHitBox)]
        expected = data_loader.load_level(1)["obstacles"]
        self.assertEqual(layers.count("ROCK"), expected["rock"])
        self.assertEqual(layers.count("MINE"), expected["mine"])
        self.assertEqual(layers.count("ROCK_SOLID"), expected["solid_rock"])

    def test_destruir_una_roca_suma_al_puntaje(self):
        rock = next(e for e, hb in self.scene.world.get_component(CHitBox) if hb.layer == "ROCK")
        pos = self.scene.world.component_for_entity(rock, CTransform).pos
        make(self.scene.world, pos, "PLAYER_BULLET", ("ROCK",), (2, 2))
        self.scene.do_update(1 / 60)
        self.assertEqual(ENGINE.state.score, CFG["rock"]["points"])


if __name__ == "__main__":
    unittest.main()
