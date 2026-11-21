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
from src.ecs.systems.s_minimap import blink_on, radar_point
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
    """Radar centrado en la nave (ver s_minimap)."""

    RECT = pygame.Rect(184, 54, 64, 80)
    SCALE = 8

    def point(self, pos, center=(500, 400)):
        return radar_point(pygame.Vector2(pos), pygame.Vector2(center), WORLD, self.RECT, self.SCALE)

    def test_el_centro_del_radar_es_la_nave(self):
        self.assertEqual(self.point((500, 400)), self.RECT.center)

    def test_lo_que_esta_a_la_derecha_y_abajo_se_ve_a_la_derecha_y_abajo_a_escala(self):
        x, y = self.point((500 + 80, 400 + 160))
        self.assertEqual((x - self.RECT.centerx, y - self.RECT.centery), (10, 20))

    def test_el_mundo_es_toroidal_un_objeto_al_otro_lado_del_borde_se_ve_cerca(self):
        # El mundo mide 1000 de ancho: x=10 está a 20 de x=990 pasando por el borde.
        x, y = self.point((10, 400), center=(990, 400))
        self.assertEqual((x - self.RECT.centerx, y - self.RECT.centery), (round(20 / self.SCALE), 0))
        _, y2 = self.point((990, 790), center=(990, 10))  # y: 790 está a 20 de y=10 por el otro lado
        self.assertEqual(y2 - self.RECT.centery, round(-20 / self.SCALE))

    def test_lo_que_queda_fuera_del_alcance_no_se_dibuja(self):
        self.assertIsNone(self.point((500 + 33 * self.SCALE, 400)))  # el radar mide 64 de ancho
        self.assertIsNone(self.point((500, 400 - 41 * self.SCALE)))  # y 80 de alto
        self.assertIsNotNone(self.point((500 + 30 * self.SCALE, 400 - 38 * self.SCALE)))

    def test_el_borde_del_marco_no_cuenta_como_alcance(self):
        edge = self.RECT.right - 1 - self.RECT.centerx
        self.assertIsNone(self.point((500 + edge * self.SCALE, 400)))

    def test_el_radar_alcanza_mas_que_la_pantalla_de_juego(self):
        """Un radar útil muestra más mundo que el viewport (176x208)."""
        self.assertGreater(self.RECT.w * self.SCALE, 176)
        self.assertGreater(self.RECT.h * self.SCALE, 208)

    def test_parpadeo_de_la_nave(self):
        cfg = {"blink_seconds": 0.3}
        self.assertTrue(blink_on(0.0, cfg))
        self.assertTrue(blink_on(0.29, cfg))
        self.assertFalse(blink_on(0.31, cfg))
        self.assertFalse(blink_on(0.59, cfg))
        self.assertTrue(blink_on(0.61, cfg))


class ColorTests(unittest.TestCase):
    def test_orden_de_claves_no_altera_el_color(self):
        self.assertEqual(color_from_cfg({"b": 0, "g": 3, "r": 9}), pygame.Color(9, 3, 0))


if __name__ == "__main__":
    unittest.main()
