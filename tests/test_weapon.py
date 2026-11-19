"""Pruebas del arma del jugador: bala delantera y trasera, enfriamiento y limpieza."""

import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_player_bullet import CPlayerBullet
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_weapon import CWeapon
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_weapon import bullet_offscreen
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase

VIEW = pygame.Rect(0, 0, 176, 208)


class OffscreenTests(unittest.TestCase):
    def test_dentro_y_fuera(self):
        self.assertFalse(bullet_offscreen(pygame.Vector2(80, 100), VIEW, 8))
        self.assertTrue(bullet_offscreen(pygame.Vector2(97, 0), VIEW, 8))
        self.assertTrue(bullet_offscreen(pygame.Vector2(0, -113), VIEW, 8))


class WeaponSceneTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.world = self.scene.world
        self.scene.blast_left = 0  # sin la cuenta de BLAST OFF!, que congela el juego
        # Estas pruebas cubren el disparo básico; el especial tiene su propia clase.
        self.world.component_for_entity(self.scene.player, CWeapon).special = False

    def tearDown(self):
        self.engine._clean()

    def bullets(self):
        return [(e, t, v) for e, (t, v, _b) in
                self.world.get_components(CTransform, CVelocity, CPlayerBullet)]

    def test_fire_crea_bala_delantera_y_trasera(self):
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_update(1 / 60)
        bs = self.bullets()
        self.assertEqual(len(bs), 2)
        vys = sorted(v.vel.y for _, _, v in bs)
        self.assertEqual(vys[0], -220)  # hacia arriba, la dirección inicial
        self.assertEqual(vys[1], 220)  # hacia atrás
        for e, _, _ in bs:
            self.assertTrue(self.world.has_component(e, CWorld))

    def test_enfriamiento_evita_rafaga(self):
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_update(0.01)
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_update(0.01)
        self.assertEqual(len(self.bullets()), 2)

    def spawned_after(self, frames):
        """Balas distintas creadas durante `frames` actualizaciones (aunque ya hayan salido)."""
        before = {e for e, _, _ in self.bullets()}
        seen = set()
        for _ in range(frames):
            self.scene.do_update(1 / 60)
            seen |= {e for e, _, _ in self.bullets()}
        return len(seen - before)

    def test_mantener_fire_repite_el_disparo(self):
        self.scene.do_action("FIRE", Phase.START)
        self.assertEqual(self.spawned_after(30), 6)  # 0,5 s con enfriamiento 0,15 s: 3 disparos
        self.scene.do_action("FIRE", Phase.END)
        self.assertEqual(self.spawned_after(30), 0)  # al soltar ya no dispara

    def test_toque_corto_no_se_pierde(self):
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_action("FIRE", Phase.END)
        self.scene.do_update(1 / 60)
        self.assertEqual(len(self.bullets()), 2)

    def test_dispara_en_diagonal(self):
        self.scene.do_action("UP", Phase.START)
        self.scene.do_action("RIGHT", Phase.START)
        self.scene.do_update(1 / 60)
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_update(1 / 60)
        v = next(v.vel for _, _, v in self.bullets() if v.vel.x > 0)
        self.assertAlmostEqual(v.x, 220 / 2 ** 0.5, places=3)
        self.assertAlmostEqual(v.y, -220 / 2 ** 0.5, places=3)

    def test_balas_se_destruyen_al_salir_de_pantalla(self):
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_action("FIRE", Phase.END)
        for _ in range(120):  # 2 s: 440 px, muy fuera del viewport
            self.scene.do_update(1 / 60)
            self.scene.do_draw(self.engine.screen)
        self.assertEqual(self.bullets(), [])

    def test_no_dispara_en_pausa(self):
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_action("FIRE", Phase.END)
        self.scene.do_action("PAUSE", Phase.START)
        self.scene.do_update(1 / 60)
        self.assertEqual(self.bullets(), [])


class SpecialShotTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.world = self.scene.world
        self.scene.blast_left = 0  # sin la cuenta de BLAST OFF!, que congela el juego

    def tearDown(self):
        self.engine._clean()

    def bullets(self):
        return [(t, v) for _, (t, v, _b) in
                self.world.get_components(CTransform, CVelocity, CPlayerBullet)]

    def texts(self):
        return [e for e, _ in self.world.get_component(CLifetime)]

    def test_disparo_especial_tres_al_frente_y_una_atras(self):
        self.world.component_for_entity(self.scene.player, CWeapon).special = True
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_update(1 / 60)
        bs = self.bullets()
        self.assertEqual(len(bs), 4)
        self.assertEqual(sorted(round(t.pos.x) - 512 for t, v in bs if v.vel.y < 0), [-11, 0, 11])
        self.assertEqual([round(t.pos.x) for t, v in bs if v.vel.y > 0], [512])

    def test_sin_habilidad_solo_dos_balas(self):
        self.world.component_for_entity(self.scene.player, CWeapon).special = False
        self.scene.do_action("FIRE", Phase.START)
        self.scene.do_update(1 / 60)
        self.assertEqual(len(self.bullets()), 2)

    def test_x_no_dispara_todavia(self):
        self.scene.do_action("SPECIAL", Phase.START)
        self.scene.do_update(1 / 60)
        self.assertEqual(len(self.bullets()), 0)

    def test_nivel_activa_la_habilidad_y_avisa(self):
        self.assertTrue(self.world.component_for_entity(self.scene.player, CWeapon).special)
        self.assertEqual(len(self.texts()), 1)

    def test_aviso_desaparece_tras_su_duracion(self):
        for _ in range(60 * 4):  # el aviso dura 3 s
            self.scene.do_update(1 / 60)
        self.assertEqual(self.texts(), [])

    def test_aviso_no_corre_en_pausa(self):
        self.scene.do_action("PAUSE", Phase.START)
        for _ in range(60 * 4):
            self.scene.do_update(1 / 60)
        self.assertEqual(len(self.texts()), 1)


if __name__ == "__main__":
    unittest.main()
