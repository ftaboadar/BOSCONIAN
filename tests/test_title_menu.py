"""Pruebas del menú del título (#27): navegación, nivel, instrucciones y créditos."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.menu import Menu

COLORS = {"normal": {"r": 255, "g": 255, "b": 255}, "selected": {"r": 255, "g": 0, "b": 0}}
ITEMS = [{"label": "A", "action": "A"}, {"label": "B", "action": "B"}, {"label": "C", "action": "C"}]


class MenuTests(unittest.TestCase):
    def setUp(self) -> None:
        self.menu = Menu(ITEMS, COLORS, 10)

    def test_empieza_en_la_primera_opcion(self):
        self.assertEqual(self.menu.current_action, "A")

    def test_baja_y_sube_con_vuelta_al_borde(self):
        self.menu.handle_action("UP", Phase.START)
        self.assertEqual(self.menu.current_action, "C")
        self.menu.handle_action("DOWN", Phase.START)
        self.assertEqual(self.menu.current_action, "A")

    def test_select_devuelve_la_accion(self):
        self.menu.handle_action("DOWN", Phase.START)
        self.assertEqual(self.menu.handle_action("SELECT", Phase.START), "B")

    def test_ignora_el_soltar_la_tecla(self):
        self.assertIsNone(self.menu.handle_action("DOWN", Phase.END))
        self.assertEqual(self.menu.current_action, "A")

    def test_cambia_la_etiqueta(self):
        self.menu.set_label("B", "NUEVA")
        self.assertEqual(self.menu.items[1]["label"], "NUEVA")


class TitleSceneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GameEngine()
        self.engine._apply_scene_change("TITLE")
        self.scene = self.engine._current_scene
        # En el título primero se ve «PUSH BUTTON TO START»; un botón abre el menú que se prueba aquí.
        self.scene.elapsed = 1.0
        self.scene.do_any_key()
        self.scene.do_update(1 / 60)
        assert self.scene.mode == "menu"

    def press(self, action: str) -> None:
        self.scene.do_action(action, Phase.START)

    def test_enter_en_jugar_va_a_la_cutscene_que_lleva_al_nivel(self):
        self.press("SELECT")
        self.assertEqual(self.engine._next_scene, "CUTSCENE")

    def test_menu_lleva_a_instrucciones_y_creditos(self):
        for steps, expected in ((2, "INSTRUCTIONS"), (1, "CREDITS")):
            for _ in range(steps):
                self.press("DOWN")
            self.press("SELECT")
            self.assertEqual(self.engine._next_scene, expected)

    def test_izquierda_derecha_cambia_el_nivel_solo_en_esa_opcion(self):
        self.scene.levels = [1, 2, 3]
        self.press("RIGHT")
        self.assertEqual(self.engine.level, 1)  # JUGAR no cambia el nivel
        self.press("DOWN")
        self.press("RIGHT")
        self.assertEqual(self.engine.level, 2)
        self.press("LEFT")
        self.press("LEFT")
        self.assertEqual(self.engine.level, 3)  # da la vuelta
        self.assertIn("3", self.scene.menu.items[1]["label"])

    def test_paginas_de_texto_vuelven_al_titulo(self):
        for name in ("INSTRUCTIONS", "CREDITS"):
            self.engine._apply_scene_change(name)
            self.engine._current_scene.do_action("BACK", Phase.START)
            self.assertEqual(self.engine._next_scene, "TITLE")

    def test_el_nivel_elegido_se_carga_al_jugar(self):
        self.engine.level = 1
        self.engine._apply_scene_change("PLAY")
        self.assertEqual(self.engine._current_scene.__class__.__name__, "PlayScene")


if __name__ == "__main__":
    unittest.main()
