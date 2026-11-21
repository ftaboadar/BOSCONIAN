"""ESC pide confirmación y, si se acepta, sale al título; cancelar conserva el progreso (#30)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.ecs.components.c_transform import CTransform
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase


class ExitToTitleTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def act(self, action):
        self.scene.do_action(action, Phase.START)

    def pos(self):
        return self.scene.world.component_for_entity(self.scene.player, CTransform).pos.copy()

    def test_esc_pide_confirmacion_y_no_sale_todavia(self):
        self.act("BACK")
        self.assertTrue(self.scene.confirm_exit)
        self.assertIsNone(self.engine._next_scene)

    def test_enter_confirma_y_sale_al_titulo(self):
        self.act("BACK")
        self.act("SELECT")
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_esc_otra_vez_cancela_y_se_sigue_jugando(self):
        self.scene.do_update(self.engine.cfg_world["blast_off"]["seconds"] + 0.1)
        self.act("BACK")
        self.act("BACK")
        self.assertFalse(self.scene.confirm_exit)
        self.assertIsNone(self.engine._next_scene)
        before = self.pos()
        self.scene.do_update(0.5)
        self.assertNotEqual(self.pos(), before)

    def test_el_mundo_esta_congelado_mientras_se_confirma(self):
        self.scene.do_update(self.engine.cfg_world["blast_off"]["seconds"] + 0.1)
        self.act("BACK")
        before = self.pos()
        for _ in range(10):
            self.scene.do_update(0.1)
        self.assertEqual(self.pos(), before)

    def test_en_pausa_esc_confirma_y_cancelar_deja_la_pausa(self):
        self.act("PAUSE")
        self.act("BACK")
        self.act("BACK")
        self.assertTrue(self.scene.paused)
        self.assertFalse(self.scene.confirm_exit)

    def test_con_la_confirmacion_abierta_otras_teclas_no_hacen_nada(self):
        self.act("BACK")
        self.act("PAUSE")
        self.act("LEFT")
        self.assertFalse(self.scene.paused)
        self.assertTrue(self.scene.confirm_exit)

    def test_el_aviso_se_dibuja(self):
        screen = pygame.Surface((256, 208))
        self.scene.do_draw(screen)
        normal = pygame.image.tobytes(screen, "RGB")
        self.act("BACK")
        screen.fill((0, 0, 0))
        self.scene.do_draw(screen)
        self.assertNotEqual(normal, pygame.image.tobytes(screen, "RGB"))

    def test_soltar_esc_no_hace_nada(self):
        self.scene.do_action("BACK", Phase.END)
        self.assertFalse(self.scene.confirm_exit)


if __name__ == "__main__":
    unittest.main()
