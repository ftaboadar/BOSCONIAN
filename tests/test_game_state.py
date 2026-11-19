"""Pruebas del estado de partida compartido (#67)."""

import os
import sys
import unittest

sys.path.insert(0, os.getcwd())

from src.engine.game_state import GameState

CFG = {"lives": 4, "hi_score": 20000, "extra_life_first": 50000, "extra_life_step": 100000,
       "life_icons_max": 4, "continue_seconds": 5}


class GameStateTests(unittest.TestCase):
    def setUp(self):
        self.s = GameState(dict(CFG))

    def test_valores_iniciales(self):
        self.assertEqual((self.s.lives, self.s.score, self.s.hi_score, self.s.level), (4, 0, 20000, 1))

    def test_hi_score_solo_sube_al_superarlo(self):
        self.s.add_score(19000)
        self.assertEqual(self.s.hi_score, 20000)
        self.s.add_score(2000)
        self.assertEqual(self.s.hi_score, 21000)

    def test_vidas_extra_en_50k_100k_y_cada_100k(self):
        for total, lives in ((49999, 4), (50000, 5), (99999, 5), (150000, 6), (250000, 7)):
            s = GameState(dict(CFG))
            s.add_score(total)
            self.assertEqual(s.lives, lives, total)

    def test_un_salto_grande_concede_todas_las_vidas_cruzadas(self):
        self.s.add_score(250000)  # cruza 50k, 150k y 250k
        self.assertEqual(self.s.lives, 7)

    def test_perder_vidas_y_game_over(self):
        for _ in range(3):
            self.s.lose_life()
        self.assertFalse(self.s.game_over)
        self.s.lose_life()
        self.assertTrue(self.s.game_over)
        self.s.lose_life()
        self.assertEqual(self.s.lives, 0)

    def test_continuar_recupera_vidas_y_pierde_puntaje_pero_conserva_record(self):
        self.s.add_score(30000)
        self.s.lives = 0
        self.s.continue_game()
        self.assertEqual((self.s.lives, self.s.score, self.s.continues_used), (4, 0, 1))
        self.assertEqual(self.s.hi_score, 30000)

    def test_reset_conserva_record_y_reinicia_lo_demas(self):
        self.s.add_score(60000)
        self.s.reset(3)
        self.assertEqual((self.s.level, self.s.lives, self.s.score, self.s.continues_used), (3, 4, 0, 0))
        self.assertEqual(self.s.hi_score, 60000)
        self.s.add_score(50000)
        self.assertEqual(self.s.lives, 5)  # el umbral de vida extra también se reinicia


if __name__ == "__main__":
    unittest.main()
