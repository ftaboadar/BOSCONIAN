"""Pruebas del movimiento del jugador: avance automático, aceleración y 8 direcciones."""

import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import esper
import pygame

from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_player import heading_from_held, system_player_movement
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class HeadingTests(unittest.TestCase):
    def test_una_tecla_da_direccion_cardinal(self):
        self.assertEqual(heading_from_held({"LEFT"}, (0, -1)), (-1, 0))

    def test_dos_teclas_dan_diagonal(self):
        self.assertEqual(heading_from_held({"UP", "RIGHT"}, (0, 1)), (1, -1))

    def test_opuestas_se_anulan_y_conserva_direccion(self):
        self.assertEqual(heading_from_held({"UP", "DOWN"}, (1, 0)), (1, 0))

    def test_sin_teclas_conserva_direccion(self):
        self.assertEqual(heading_from_held(set(), (0, 1)), (0, 1))


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()
        self.ship = CPlayerShip((0, -1), max_speed=80, acceleration=40)
        self.e = self.w.create_entity(self.ship, CVelocity(pygame.Vector2()))

    def test_arranca_quieta_y_acelera_sin_teclas(self):
        system_player_movement(self.w, 0.5)
        v = self.w.component_for_entity(self.e, CVelocity).vel
        self.assertAlmostEqual(v.y, -20)
        self.assertAlmostEqual(v.x, 0)

    def test_rapidez_limitada_al_maximo(self):
        for _ in range(100):
            system_player_movement(self.w, 0.1)
        self.assertEqual(self.ship.speed, 80)

    def test_diagonal_no_es_mas_rapida(self):
        self.ship.held = {"UP", "RIGHT"}
        for _ in range(100):
            system_player_movement(self.w, 0.1)
        self.assertAlmostEqual(self.w.component_for_entity(self.e, CVelocity).vel.length(), 80)

    def test_girar_conserva_la_rapidez(self):
        for _ in range(100):
            system_player_movement(self.w, 0.1)
        self.ship.held = {"LEFT"}
        system_player_movement(self.w, 0.016)
        v = self.w.component_for_entity(self.e, CVelocity).vel
        self.assertAlmostEqual(v.x, -80)
        self.assertAlmostEqual(v.y, 0)


class PlaySceneInputTests(unittest.TestCase):
    def setUp(self):
        # Los obstáculos del nivel se reparten al azar: con semilla fija la nave no choca
        # con uno durante la prueba y el resultado no depende del orden de las pruebas.
        random.seed(0)
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.scene.blast_left = 0.0  # sin cuenta regresiva
        self.ship = self.scene.world.component_for_entity(self.scene.player, CPlayerShip)

    def tearDown(self):
        self.engine._clean()

    def test_mantener_y_soltar_tecla(self):
        self.scene.do_action("LEFT", Phase.START)
        self.scene.do_update(0.1)
        self.assertEqual(self.ship.heading, (-1, 0))
        self.scene.do_action("LEFT", Phase.END)
        self.assertEqual(self.ship.held, set())

    def test_soltar_tecla_en_pausa_se_registra(self):
        self.scene.do_action("UP", Phase.START)
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_action("UP", Phase.END)
        self.assertEqual(self.ship.held, set())

    def test_avanza_sola_y_da_la_vuelta_al_mundo(self):
        pos = self.scene.world.component_for_entity(self.scene.player, CTransform).pos
        pos.y = 1.0
        for _ in range(600):
            self.scene.do_update(1 / 60)
        # 10 s: 106,7 px acelerando (hasta 80 px/s con a=30) + 586,7 px a velocidad máxima
        # = 693,3 px hacia arriba; desde y=1 cruza la costura y queda en 1 - 693,3 + 1024.
        self.assertAlmostEqual(pos.y, 331.7, delta=1.0)
        self.scene.do_draw(self.engine.screen)


if __name__ == "__main__":
    unittest.main()
