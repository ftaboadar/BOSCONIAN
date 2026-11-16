"""Pruebas del hito 2: estrellas, cámara, wraparound y minimapa (sin ventana)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_minimap import minimap_point
from src.ecs.systems.s_star import star_alpha, system_star_fall, system_star_parallax
from src.ecs.systems.s_wraparound import system_wraparound
from src.ecs.components.c_star import CStar
from src.engine.camera import Camera, wrap_delta
from src.engine.service_locator import color_from_cfg

WORLD = pygame.Vector2(1000, 800)


class WrapTests(unittest.TestCase):
    def test_wrap_delta_toma_el_camino_corto(self):
        d = wrap_delta(pygame.Vector2(990, -790), WORLD)
        self.assertEqual((d.x, d.y), (-10, 10))

    def test_wraparound_horizontal_y_vertical(self):
        w = esper.World()
        e = w.create_entity(CTransform(pygame.Vector2(1005, -5)), CWorld())
        system_wraparound(w, WORLD)
        p = w.component_for_entity(e, CTransform).pos
        self.assertEqual((p.x, p.y), (5, 795))

    def test_wraparound_ignora_entidades_sin_cworld(self):
        w = esper.World()
        e = w.create_entity(CTransform(pygame.Vector2(1005, 0)))
        system_wraparound(w, WORLD)
        self.assertEqual(w.component_for_entity(e, CTransform).pos.x, 1005)


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.cam = Camera(WORLD, pygame.Rect(0, 0, 176, 208))

    def test_objetivo_queda_en_el_centro_del_viewport(self):
        self.cam.follow(pygame.Vector2(500, 400))
        p = self.cam.world_to_screen(pygame.Vector2(500, 400))
        self.assertEqual((p.x, p.y), (88, 104))

    def test_objeto_cruzando_el_borde_del_mundo_se_ve_continuo(self):
        self.cam.follow(pygame.Vector2(5, 400))
        p = self.cam.world_to_screen(pygame.Vector2(995, 400))  # 10 px a la izquierda
        self.assertEqual(p.x, 88 - 10)

    def test_delta_de_camara_atraviesa_el_borde(self):
        self.cam.follow(pygame.Vector2(995, 400))
        self.cam.follow(pygame.Vector2(5, 400))
        self.assertEqual(self.cam.delta.x, 10)


class StarTests(unittest.TestCase):
    def test_alfa_recorre_0_a_255(self):
        vals = [star_alpha(i / 100) for i in range(100)]
        self.assertEqual(min(vals), 0)
        self.assertGreaterEqual(max(vals), 250)
        self.assertTrue(all(0 <= v <= 255 for v in vals))

    def _star_world(self):
        w = esper.World()
        e = w.create_entity(CTransform(pygame.Vector2(10, 10)),
                            CStar(pygame.Color(255, 0, 0), 0.3, 0.0))
        return w, e

    def test_parallax_se_mueve_en_sentido_contrario_y_mas_lento(self):
        w, e = self._star_world()
        area = pygame.Rect(0, 0, 176, 208)
        system_star_parallax(w, area, pygame.Vector2(10, 0), 0.5)
        self.assertEqual(w.component_for_entity(e, CTransform).pos.x, 5)

    def test_en_menu_caen_hacia_abajo_con_vuelta(self):
        w, e = self._star_world()
        area = pygame.Rect(0, 0, 256, 208)
        system_star_fall(w, area, 100, 1.0)
        self.assertEqual(w.component_for_entity(e, CTransform).pos.y, (10 + 100) % 208)
        system_star_fall(w, area, 100, 1.0)
        self.assertEqual(w.component_for_entity(e, CTransform).pos.y, (10 + 200) % 208)


class MinimapTests(unittest.TestCase):
    def test_extremos_y_vuelta_toroidal(self):
        rect = pygame.Rect(184, 64, 64, 64)
        self.assertEqual(minimap_point(pygame.Vector2(0, 0), WORLD, rect), (184, 64))
        self.assertEqual(minimap_point(pygame.Vector2(1000, 800), WORLD, rect), (184, 64))
        self.assertEqual(minimap_point(pygame.Vector2(-1, 0), WORLD, rect)[0], 246)


class ColorTests(unittest.TestCase):
    def test_orden_de_claves_no_altera_el_color(self):
        self.assertEqual(color_from_cfg({"b": 0, "g": 3, "r": 9}), pygame.Color(9, 3, 0))


if __name__ == "__main__":
    unittest.main()
