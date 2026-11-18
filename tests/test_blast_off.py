"""Pruebas de BLAST OFF! (#28): el jugador no se mueve hasta que acaba la cuenta."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

from src.ecs.components.c_transform import CTransform
from src.engine.game_engine import GameEngine


class BlastOffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def pos(self):
        return self.scene.world.component_for_entity(self.scene.player, CTransform).pos.copy()

    def test_empieza_con_la_cuenta_activa(self):
        self.assertEqual(self.scene.blast_left, self.engine.cfg_world["blast_off"]["seconds"])

    def test_el_jugador_no_se_mueve_durante_blast_off(self):
        start = self.pos()
        self.scene.do_update(0.5)
        self.assertEqual(self.pos(), start)
        self.assertGreater(self.scene.blast_left, 0)

    def test_se_mueve_cuando_termina(self):
        start = self.pos()
        self.scene.do_update(self.engine.cfg_world["blast_off"]["seconds"] + 0.1)
        self.assertEqual(self.scene.blast_left, 0)
        self.scene.do_update(0.5)
        self.assertNotEqual(self.pos(), start)

    def test_el_texto_se_dibuja_solo_durante_la_cuenta(self):
        import pygame
        screen = pygame.Surface((256, 208))
        self.scene.do_draw(screen)
        with_text = pygame.image.tobytes(screen, "RGB")
        self.scene.blast_left = 0
        screen.fill((0, 0, 0))
        self.scene.do_draw(screen)
        self.assertNotEqual(with_text, pygame.image.tobytes(screen, "RGB"))


if __name__ == "__main__":
    unittest.main()
