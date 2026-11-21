"""Pruebas de las escenas de victoria (#31) y derrota con continuar (#32)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class EndSceneTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.state = self.engine.state

    def open(self, name):
        self.engine._apply_scene_change(name)
        return self.engine._current_scene

    def test_victoria_muestra_vidas_y_continuaciones_usadas(self):
        self.state.continues_used = 2
        for _ in range(3):
            self.state.lose_life()
        scene = self.open("VICTORY")
        lines = scene.page()["lines"]
        self.assertIn("VIDAS USADAS 3", lines)  # las que se perdieron, no las que quedan
        self.assertIn("CONTINUACIONES 2", lines)

    def test_ganar_sin_morir_muestra_cero_vidas_usadas(self):
        self.assertIn("VIDAS USADAS 0", self.open("VICTORY").page()["lines"])

    def test_las_vidas_usadas_se_acumulan_al_continuar_y_se_olvidan_en_partida_nueva(self):
        for _ in range(5):
            self.state.lose_life()  # las 4 y la del cero: game over
        self.assertTrue(self.state.game_over)
        self.state.continue_game()
        self.state.lose_life()
        self.assertEqual(self.state.lives_used, 6)
        self.engine.start_game()
        self.assertEqual(self.state.lives_used, 0)

    def test_victoria_vuelve_al_titulo_con_cualquier_tecla_tras_la_gracia(self):
        scene = self.open("VICTORY")
        scene.do_any_key()  # demasiado pronto: se ignora
        self.assertIsNone(self.engine._next_scene)
        scene.do_update(1.0)
        scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_derrota_continuar_recupera_vidas_pierde_puntaje_y_mantiene_nivel(self):
        self.state.level, self.state.lives = 3, 0
        self.state.add_score(30000)
        self.state.lives = 0
        scene = self.open("DEFEAT")
        scene.do_action("SELECT", Phase.START)
        self.assertEqual(self.engine._next_scene, "PLAY")
        self.assertEqual((self.state.lives, self.state.score, self.state.level), (4, 0, 3))
        self.assertEqual(self.state.continues_used, 1)
        self.assertEqual(self.state.hi_score, 30000)

    def test_derrota_sin_continuar_vuelve_al_titulo_a_los_5_segundos(self):
        scene = self.open("DEFEAT")
        scene.do_update(4.9)
        self.assertIsNone(self.engine._next_scene)
        scene.do_update(0.2)
        self.assertEqual(self.engine._next_scene, "TITLE")
        self.assertEqual(self.state.continues_used, 0)

    def test_derrota_esc_vuelve_al_titulo_sin_continuar(self):
        scene = self.open("DEFEAT")
        scene.do_action("BACK", Phase.START)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_la_cuenta_regresiva_se_dibuja_y_cambia(self):
        scene = self.open("DEFEAT")
        screen = pygame.Surface((256, 208))
        scene.do_draw(screen)
        a = pygame.image.tobytes(screen, "RGB")
        scene.do_update(2.0)
        screen.fill((0, 0, 0))
        scene.do_draw(screen)
        self.assertNotEqual(a, pygame.image.tobytes(screen, "RGB"))

    def test_tras_continuar_se_puede_jugar_el_mismo_nivel(self):
        self.state.level, self.state.lives = 1, 0
        scene = self.open("DEFEAT")
        scene.do_action("SELECT", Phase.START)
        play = self.open(self.engine._next_scene)
        self.assertEqual(play.round, 1)
        self.assertEqual(self.state.lives, 4)


if __name__ == "__main__":
    unittest.main()
