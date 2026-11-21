"""Pruebas del panel lateral (#88): radar centrado en la nave, indicador CONDITION y vidas
como mini-naves."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_minimap import radar_point, radar_rect, system_minimap_rendering
from src.engine.data_loader import load_json
from src.engine.game_engine import GameEngine
from src.engine.game_state import ALERTS, GameState
from src.engine.hud import CONDITION_COLORS, ICON_SPACING, ICONS_Y, PANEL_CX, ROUND_Y, Hud
from src.engine.service_locator import ServiceLocator, color_from_cfg

CFG = load_json("assets/cfg/world.json")["minimap"]
WORLD = pygame.Vector2(1024, 1024)
BLACK = pygame.Color(0, 0, 0)


def lit(surface: pygame.Surface, rect: pygame.Rect) -> bool:
    """¿Hay algún píxel distinto del fondo negro dentro de `rect`?"""
    return any(surface.get_at((x, y))[:3] != (0, 0, 0)
               for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom))


class PanelTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.state = GameState()
        r = load_json("assets/cfg/player.json")["sprite_rect"]
        icon = ServiceLocator.images.get("ships").subsurface(
            pygame.Rect(r["x"], r["y"], r["w"], r["h"])).copy()
        self.hud = Hud(ServiceLocator.fonts.get("main"), self.state.cfg["life_icons_max"], icon)
        self.icon_size = icon.get_size()
        self.screen = pygame.Surface((256, 208))

    def draw(self):
        self.screen.fill(BLACK)
        self.hud.draw(self.screen, self.state, 1)
        self.hud.draw_cheat(self.screen, self.state)

    def icon_rect(self, i, shown):
        left = PANEL_CX - shown * ICON_SPACING // 2
        return pygame.Rect(left + i * ICON_SPACING, ICONS_Y, *self.icon_size)


class LivesIconTests(PanelTestCase):
    def test_las_vidas_se_dibujan_como_mini_naves_una_por_vida(self):
        for lives in (1, 2, 3, 4):
            self.state.lives = lives
            self.draw()
            for i in range(lives):
                self.assertTrue(lit(self.screen, self.icon_rect(i, lives)), (lives, i))

    def test_con_menos_vidas_no_se_dibujan_las_demas(self):
        self.state.lives = 2
        self.draw()
        self.assertFalse(lit(self.screen, pygame.Rect(self.icon_rect(0, 2).left - 24, ICONS_Y, 20, 17)))

    def test_la_mini_nave_es_el_sprite_de_la_nave_y_no_un_triangulo(self):
        self.state.lives = 1
        self.draw()
        rect = self.icon_rect(0, 1)
        colors = {tuple(self.screen.get_at((x, y))) for x in range(rect.left, rect.right)
                  for y in range(rect.top, rect.bottom)}
        self.assertGreater(len(colors), 3)  # el sprite tiene varios colores; el triángulo era blanco
        self.assertGreaterEqual(rect.width, 14)

    def test_con_mas_vidas_que_iconos_se_ve_el_numero_total_y_solo_los_iconos_maximos(self):
        self.state.lives = 7
        self.draw()
        self.assertTrue(lit(self.screen, pygame.Rect(236, 198, 20, 10)))  # el número, abajo a la derecha
        fourth = self.icon_rect(3, 4)
        self.assertTrue(lit(self.screen, fourth))
        self.assertFalse(lit(self.screen, pygame.Rect(fourth.right, ICONS_Y, 8, self.icon_size[1])))  # ni un quinto

    def test_sin_exceso_no_hay_numero(self):
        self.state.lives = 4
        self.draw()
        self.assertFalse(lit(self.screen, pygame.Rect(236, 198, 20, 10)))


class ConditionTests(PanelTestCase):
    REGION = pygame.Rect(176, 146, 80, 10)

    def colors_in_region(self):
        return {tuple(self.screen.get_at((x, y)))[:3] for x in range(self.REGION.left, self.REGION.right)
                for y in range(self.REGION.top, self.REGION.bottom)}

    def test_el_estado_arranca_en_verde(self):
        self.assertEqual(GameState().alert, "GREEN")
        self.assertEqual(ALERTS, ("GREEN", "YELLOW", "RED"))

    def test_cada_alerta_se_pinta_de_su_color_y_de_ningun_otro(self):
        for alert, color in CONDITION_COLORS.items():
            self.state.alert = alert
            self.draw()
            seen = self.colors_in_region()
            self.assertIn(tuple(color)[:3], seen, alert)
            for other, other_color in CONDITION_COLORS.items():
                if other != alert:
                    self.assertNotIn(tuple(other_color)[:3], seen, f"{alert} muestra el color de {other}")

    def test_todo_nivel_empieza_en_verde(self):
        self.engine.state.alert = "RED"
        self.engine._apply_scene_change("PLAY")
        self.assertEqual(self.engine.state.alert, "GREEN")

    def test_una_partida_nueva_vuelve_a_verde(self):
        self.state.alert = "RED"
        self.state.reset()
        self.assertEqual(self.state.alert, "GREEN")


class LayoutTests(PanelTestCase):
    def test_el_panel_no_dibuja_fuera_de_su_zona(self):
        self.state.lives, self.state.cheat, self.state.alert = 9, True, "YELLOW"
        self.draw()
        world = esper.World()
        world.create_entity(CTransform(pygame.Vector2(512, 512)), CMinimapTrack("player"))
        system_minimap_rendering(world, self.screen, CFG, WORLD, pygame.Vector2(512, 512), 0.0)
        self.assertFalse(lit(self.screen, pygame.Rect(0, 0, 176, 208)), "el panel invade el campo de juego")

    def test_las_filas_van_en_orden_y_caben_en_pantalla(self):
        radar = radar_rect(CFG)
        self.assertGreater(radar.top, 48)                       # bajo el puntaje del jugador
        self.assertLess(radar.bottom, 141 - 4)                  # sobre CONDITION
        self.assertLess(150 + 4, ICONS_Y)                       # CONDITION y CHEAT sobre las mini-naves
        self.assertLess(ICONS_Y + self.icon_size[1], ROUND_Y - 4)
        self.assertLessEqual(ROUND_Y + 4, 208)
        self.assertGreaterEqual(radar.left, 176)
        self.assertLessEqual(radar.right, 256)

    def test_el_radar_es_mas_alto_que_ancho_y_mas_grande_que_el_minimapa_anterior(self):
        radar = radar_rect(CFG)
        self.assertGreater(radar.height, radar.width)
        self.assertGreater(radar.width * radar.height, 64 * 64)


class RadarRenderTests(PanelTestCase):
    def render(self, entities, center=(512, 512), elapsed=0.0):
        world = esper.World()
        for kind, pos in entities:
            world.create_entity(CTransform(pygame.Vector2(pos)), CMinimapTrack(kind))
        self.screen.fill(BLACK)
        system_minimap_rendering(world, self.screen, CFG, WORLD, pygame.Vector2(center), elapsed)
        return self.screen

    def test_la_nave_se_ve_en_el_centro_y_parpadea(self):
        centre = radar_rect(CFG).center
        on = self.render([("player", (512, 512))], elapsed=0.0)
        self.assertEqual(tuple(on.get_at(centre))[:3], (255, 255, 255))
        off = self.render([("player", (512, 512))], elapsed=CFG["blink_seconds"] + 0.01)
        self.assertNotEqual(tuple(off.get_at(centre))[:3], (255, 255, 255))

    def test_una_base_aparece_a_escala_y_con_el_nucleo_de_otro_color(self):
        pos = (512 + 80, 512 - 160)
        point = radar_point(pygame.Vector2(pos), pygame.Vector2(512, 512), WORLD, radar_rect(CFG), CFG["scale"])
        screen = self.render([("base", pos)])
        self.assertEqual(tuple(screen.get_at((point[0] + 1, point[1])))[:3], (255, 64, 64))
        self.assertEqual(tuple(screen.get_at(point))[:3], tuple(color_from_cfg(CFG["base_core_color"]))[:3])

    def test_una_base_fuera_del_alcance_no_se_dibuja(self):
        rect = radar_rect(CFG)
        before = pygame.Surface((256, 208)); before.fill(BLACK)
        system_minimap_rendering(esper.World(), before, CFG, WORLD, pygame.Vector2(512, 512), 0.0)
        far = self.render([("base", (512 + 400, 512))])  # 50 px a la derecha: el radar llega a ~31
        self.assertEqual(pygame.image.tobytes(far.subsurface(rect), "RGB"),
                         pygame.image.tobytes(before.subsurface(rect), "RGB"))

    def test_una_base_al_otro_lado_del_borde_del_mundo_se_ve_cerca_de_la_nave(self):
        screen = self.render([("base", (10, 512))], center=(1000, 512))  # a 34 px del mundo, no a 990
        self.assertTrue(lit(screen, radar_rect(CFG).inflate(-2, -2)))

    def test_el_radar_sigue_el_centro_se_mueve_con_la_nave(self):
        base = ("base", (700, 512))
        a = self.render([base], center=(512, 512)).copy()
        b = self.render([base], center=(600, 512))
        self.assertNotEqual(pygame.image.tobytes(a, "RGB"), pygame.image.tobytes(b, "RGB"))

    def test_nada_se_dibuja_fuera_del_marco_aunque_la_marca_este_en_el_borde(self):
        rect = radar_rect(CFG)
        edge = (512 + (rect.w // 2 - 3) * CFG["scale"], 512)  # base casi en el borde derecho
        screen = self.render([("base", edge)])
        self.assertFalse(lit(screen, pygame.Rect(rect.right, rect.top, 8, rect.height)))


class PlaySceneIntegrationTests(PanelTestCase):
    def test_el_nivel_dibuja_panel_y_radar_sin_fallar_y_cambia_con_la_alerta(self):
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.blast_left = 0
        scene.do_update(1 / 60)
        self.screen.fill(BLACK)
        scene.do_draw(self.screen)
        green = self.screen.copy()
        self.engine.state.alert = "RED"
        self.screen.fill(BLACK)
        scene.do_draw(self.screen)
        self.assertNotEqual(pygame.image.tobytes(green, "RGB"), pygame.image.tobytes(self.screen, "RGB"))

    def test_en_pausa_no_se_ve_el_radar(self):
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.blast_left = 0
        scene.paused = True
        self.screen.fill(BLACK)
        scene.do_draw(self.screen)
        self.assertFalse(lit(self.screen, radar_rect(CFG)))


if __name__ == "__main__":
    unittest.main()
