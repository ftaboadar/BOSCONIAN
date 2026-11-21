"""Pruebas del modo atractor (#36): inactividad, demo, instrucciones e interrupción."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_transform import CTransform
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class AttractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GameEngine()
        self.cfg = self.engine.cfg_menu["attract"]

    def go(self, name: str):
        self.engine._apply_scene_change(name)
        return self.engine._current_scene

    def test_la_inactividad_en_el_titulo_arranca_el_atractor(self):
        title = self.go("TITLE")
        title.do_update(self.cfg["idle_seconds"] - 1)
        self.assertIsNone(self.engine._next_scene)
        title.do_update(2)
        self.assertEqual(self.engine._next_scene, "ATTRACT")

    def test_una_tecla_reinicia_la_inactividad(self):
        title = self.go("TITLE")
        title.do_update(self.cfg["idle_seconds"] - 1)
        title.do_any_key()
        title.do_update(self.cfg["idle_seconds"] - 1)
        self.assertIsNone(self.engine._next_scene)

    def test_la_demo_se_juega_sola_sin_cuenta_regresiva(self):
        demo = self.go("ATTRACT")
        start = demo.world.component_for_entity(demo.player, CTransform).pos.copy()
        demo.do_update(0.5)
        self.assertNotEqual(demo.world.component_for_entity(demo.player, CTransform).pos, start)

    def test_la_demo_cambia_de_direccion(self):
        demo = self.go("ATTRACT")
        # Sin hitbox la nave no puede chocar: la prueba no depende de dónde caen los obstáculos.
        demo.world.remove_component(demo.player, CHitBox)
        seen = set()
        for _ in range(60):
            demo.do_update(self.cfg["turn_every"])
            if self.engine._next_scene:
                break
            seen.add(frozenset(demo.world.component_for_entity(demo.player, CPlayerShip).held))
        self.assertGreater(len(seen), 1)

    def test_morir_en_la_demo_no_cuesta_vidas(self):
        demo = self.go("ATTRACT")
        lives = self.engine.state.lives
        demo.world.add_component(demo.player, CDestroy())
        for _ in range(600):
            demo.do_update(1 / 60)
            if self.engine._next_scene:
                break
        self.assertEqual(self.engine._next_scene, "ATTRACT_INFO")
        self.assertEqual(self.engine.state.lives, lives)

    def test_el_jugador_no_controla_la_demo(self):
        demo = self.go("ATTRACT")
        ship = demo.world.component_for_entity(demo.player, CPlayerShip)
        before = set(ship.held)
        demo.do_action("DOWN", Phase.START)
        self.assertEqual(ship.held, before)

    def test_tras_la_demo_van_las_instrucciones_y_luego_el_titulo(self):
        demo = self.go("ATTRACT")
        demo.do_update(self.cfg["demo_seconds"] + 0.1)
        self.assertEqual(self.engine._next_scene, "ATTRACT_INFO")
        info = self.go("ATTRACT_INFO")
        info.do_update(self.cfg["instructions_seconds"] + 0.1)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_cualquier_tecla_incluso_sin_mapear_interrumpe(self):
        for name in ("ATTRACT", "ATTRACT_INFO"):
            self.go(name)
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
            self.engine._process_events()
            self.assertEqual(self.engine._next_scene, "TITLE")

    def test_las_paginas_normales_no_se_ven_afectadas(self):
        info = self.go("INSTRUCTIONS")
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_q))
        self.engine._process_events()
        self.assertIsNone(self.engine._next_scene)


if __name__ == "__main__":
    unittest.main()
