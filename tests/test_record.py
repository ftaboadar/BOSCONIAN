"""Pruebas de la escena de felicitación por récord (#43): se muestra en victoria o derrota
si se superó el HI-SCORE de la partida."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine.game_engine import GameEngine
from src.engine.game_state import GameState
from src.engine.input.command import Phase
from src.engine.level_flow import after_game_end


class RecordStateTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.start = self.state.hi_score

    def test_sin_superar_el_hi_score_no_hay_record(self):
        self.state.add_score(self.start)  # igualarlo no es superarlo
        self.assertFalse(self.state.broke_record)

    def test_superar_el_hi_score_es_record(self):
        self.state.add_score(self.start + 1)
        self.assertTrue(self.state.broke_record)

    def test_continuar_no_borra_el_record(self):
        self.state.add_score(self.start + 500)
        self.state.continue_game()  # pierde el puntaje, pero el récord ya quedó subido
        self.assertEqual(self.state.score, 0)
        self.assertTrue(self.state.broke_record)

    def test_nueva_partida_debe_superar_el_nuevo_record(self):
        self.state.add_score(self.start + 500)
        self.state.reset()
        self.assertFalse(self.state.broke_record)
        self.state.add_score(self.start + 500)  # igual al récord anterior: no lo supera
        self.assertFalse(self.state.broke_record)
        self.state.add_score(1)
        self.assertTrue(self.state.broke_record)

    def test_el_flujo_decide_entre_felicitacion_y_titulo(self):
        self.assertEqual(after_game_end(self.state), "TITLE")
        self.state.add_score(self.start + 1)
        self.assertEqual(after_game_end(self.state), "RECORD")


class RecordSceneFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.state = self.engine.state
        self.start = self.state.hi_score

    def open(self, name):
        self.engine._apply_scene_change(name)
        return self.engine._current_scene

    def beat_record(self):
        self.state.add_score(self.start + 1234)

    def test_victoria_con_record_pasa_por_la_felicitacion(self):
        self.beat_record()
        scene = self.open("VICTORY")
        scene.do_update(1.0)
        scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "RECORD")

    def test_victoria_sin_record_va_directo_al_titulo(self):
        scene = self.open("VICTORY")
        scene.do_update(1.0)
        scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_derrota_con_record_pasa_por_la_felicitacion_al_acabarse_el_tiempo(self):
        self.beat_record()
        self.state.lives = 0
        scene = self.open("DEFEAT")
        scene.do_update(self.state.cfg["continue_seconds"] + 0.1)
        self.assertEqual(self.engine._next_scene, "RECORD")

    def test_derrota_con_record_y_esc_tambien_felicita(self):
        self.beat_record()
        scene = self.open("DEFEAT")
        scene.do_action("BACK", Phase.START)
        self.assertEqual(self.engine._next_scene, "RECORD")

    def test_derrota_sin_record_vuelve_al_titulo(self):
        scene = self.open("DEFEAT")
        scene.do_update(self.state.cfg["continue_seconds"] + 0.1)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_continuar_tras_la_derrota_no_felicita_todavia(self):
        self.beat_record()
        scene = self.open("DEFEAT")
        scene.do_action("SELECT", Phase.START)
        self.assertEqual(self.engine._next_scene, "PLAY")


class RecordSceneTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.state = self.engine.state
        self.state.add_score(self.state.hi_score + 777)
        self.engine._apply_scene_change("RECORD")
        self.scene = self.engine._current_scene

    def test_muestra_el_nuevo_record(self):
        page = self.scene.page()
        self.assertEqual(page["title"], "NUEVO RECORD")
        self.assertIn(f"HI-SCORE {self.state.hi_score}", page["lines"])

    def test_cualquier_tecla_vuelve_al_titulo_tras_la_gracia(self):
        self.scene.do_any_key()  # demasiado pronto: evita saltarla con la tecla del juego
        self.assertIsNone(self.engine._next_scene)
        self.scene.do_update(1.0)
        self.scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_se_dibuja_sin_fallar(self):
        self.scene.do_update(0.1)
        self.scene.do_draw(pygame.Surface((256, 208)))

    def test_al_volver_a_jugar_el_record_nuevo_es_el_que_hay_que_superar(self):
        self.engine.start_game()
        self.assertFalse(self.state.broke_record)


if __name__ == "__main__":
    unittest.main()
