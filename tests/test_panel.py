"""Pruebas del panel lateral (#88): distribución medida del Bosconian original (barra de 64 px a la
derecha de un campo de 192 px), radar centrado en la nave, indicador CONDITION y mini-naves."""

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
from src.engine.hud import (BAR_H, BAR_Y, CONDITION_COLORS, ICON_SPACING, ICONS_Y, LETTER_ADVANCE,
                            RED, ROWS, WHITE)
from src.engine.service_locator import color_from_cfg

CFG = load_json("assets/cfg/world.json")["minimap"]
WORLD = pygame.Vector2(1024, 1024)
BLACK = pygame.Color(0, 0, 0)


def lit(surface: pygame.Surface, rect: pygame.Rect) -> bool:
    """¿Hay algún píxel distinto del fondo negro dentro de `rect`?"""
    return any(surface.get_at((x, y))[:3] != (0, 0, 0)
               for x in range(rect.left, rect.right) for y in range(rect.top, rect.bottom))


def colors(surface: pygame.Surface, rect: pygame.Rect) -> set:
    return {tuple(surface.get_at((x, y)))[:3] for x in range(rect.left, rect.right)
            for y in range(rect.top, rect.bottom)}


class PanelTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.state = GameState()
        self.hud = self.engine.hud
        self.panel = self.hud.panel
        self.icon_size = self.hud.icon.get_size()
        self.screen = pygame.Surface((256, 208))

    def draw(self):
        self.screen.fill(BLACK)
        self.hud.draw(self.screen, self.state, 1)
        self.hud.draw_cheat(self.screen, self.state)

    def row(self, name, height=8):
        return pygame.Rect(self.panel.left, ROWS[name], self.panel.w, height)

    def icon_rect(self, i, shown):
        left = self.panel.centerx - shown * ICON_SPACING // 2
        return pygame.Rect(left + i * ICON_SPACING, ICONS_Y, *self.icon_size)


class OriginalLayoutTests(PanelTestCase):
    """Medidas tomadas de capturas del original: campo de 192 px, barra de 64 px."""

    def test_el_campo_mide_192_y_la_barra_64(self):
        self.assertEqual(self.engine.viewport.w, 192)
        self.assertEqual(self.panel, pygame.Rect(192, 0, 64, 208))

    def test_el_radar_ocupa_todo_el_ancho_de_la_barra_y_mide_96_de_alto(self):
        radar = radar_rect(CFG)
        self.assertEqual((radar.left, radar.w, radar.top, radar.h), (192, 64, 80, 96))

    def test_el_radar_es_lavanda_y_sin_marco(self):
        self.assertNotIn("border_color", CFG)
        screen = pygame.Surface((256, 208))
        screen.fill(BLACK)
        system_minimap_rendering(esper.World(), screen, CFG, WORLD, pygame.Vector2(), 0.0)
        radar = radar_rect(CFG)
        self.assertEqual(colors(screen, radar), {tuple(color_from_cfg(CFG["bg_color"]))[:3]})
        self.assertFalse(lit(screen, pygame.Rect(0, 0, 192, 208)))
        self.assertGreater(CFG["bg_color"]["b"], CFG["bg_color"]["r"])  # azulada

    def test_hi_score_es_rojo_y_ocupa_todo_el_ancho(self):
        self.draw()
        label = self.row("hi_label")
        self.assertIn(tuple(RED)[:3], colors(self.screen, label))
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.left, label.top, 6, 8)))   # empieza en el borde izquierdo
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.right - 6, label.top, 6, 8)))  # y llega al derecho

    def test_los_valores_van_alineados_a_la_derecha_y_1up_a_la_izquierda(self):
        self.state.score = 7650
        self.draw()
        value = self.row("up_value")
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.right - 8, value.top, 8, 8)))  # el último dígito toca el borde
        self.assertFalse(lit(self.screen, pygame.Rect(self.panel.left, value.top, 16, 8)))     # a la izquierda no hay nada
        label = self.row("up_label")
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.left, label.top, 24, 8)))      # 1UP a la izquierda
        self.assertFalse(lit(self.screen, pygame.Rect(self.panel.left + 32, label.top, 32, 8)))

    def test_round_tiene_la_etiqueta_a_la_izquierda_y_el_numero_a_la_derecha(self):
        self.draw()
        row = self.row("round")
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.left, row.top, 40, 8)))
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.right - 8, row.top, 8, 8)))
        self.assertFalse(lit(self.screen, pygame.Rect(self.panel.left + 42, row.top, 12, 8)))  # hueco entre ambos
        self.assertEqual(ROWS["round"] + 8, 208)  # pegado al borde de abajo

    def test_condition_cabe_en_la_barra_aunque_tenga_nueve_letras(self):
        self.assertLessEqual(len("CONDITION") * LETTER_ADVANCE, self.panel.w)
        self.draw()
        self.assertTrue(lit(self.screen, pygame.Rect(self.panel.right - 8, ROWS["condition"], 8, 8)))  # llega a la última letra


class LivesIconTests(PanelTestCase):
    def test_las_vidas_se_dibujan_como_mini_naves_una_por_vida(self):
        for lives in (1, 2, 3, 4):
            self.state.lives = lives
            self.draw()
            for i in range(lives):
                self.assertTrue(lit(self.screen, self.icon_rect(i, lives)), (lives, i))

    def test_cuatro_mini_naves_llenan_justo_el_ancho_de_la_barra(self):
        self.assertEqual(4 * ICON_SPACING, self.panel.w)
        self.state.lives = 4
        self.draw()
        self.assertEqual(self.icon_rect(0, 4).left, self.panel.left)

    def test_con_menos_vidas_no_se_dibujan_las_demas(self):
        self.state.lives = 2
        self.draw()
        self.assertFalse(lit(self.screen, pygame.Rect(self.icon_rect(0, 2).left - 24, ICONS_Y, 20, 17)))

    def test_la_mini_nave_es_el_sprite_de_la_nave_y_no_un_triangulo(self):
        self.state.lives = 1
        self.draw()
        rect = self.icon_rect(0, 1)
        self.assertGreater(len(colors(self.screen, rect)), 3)
        self.assertGreaterEqual(rect.width, 14)

    def test_con_mas_vidas_que_iconos_se_ve_el_total_y_solo_los_iconos_maximos(self):
        self.state.lives = 7
        self.draw()
        fourth = self.icon_rect(3, 4)
        self.assertTrue(lit(self.screen, fourth))
        self.assertFalse(lit(self.screen, pygame.Rect(self.panel.left - 16, ICONS_Y, 16, self.icon_size[1])))  # no hay quinto icono
        total = pygame.Rect(self.panel.right - 10, ICONS_Y + self.icon_size[1] - 8, 10, 8)
        self.assertIn((255, 255, 255), colors(self.screen, total))  # el 7, en blanco, abajo a la derecha

    def test_el_total_solo_aparece_cuando_hay_mas_vidas_que_iconos(self):
        spot = pygame.Rect(self.panel.right - 10, ICONS_Y + self.icon_size[1] - 8, 10, 8)

        def spot_bytes(lives):
            self.state.lives = lives
            self.draw()
            return pygame.image.tobytes(self.screen.subsurface(spot), "RGB")

        self.assertEqual(spot_bytes(3), spot_bytes(3))
        four, five, six = spot_bytes(4), spot_bytes(5), spot_bytes(6)
        self.assertNotEqual(four, five)   # a partir de 5 aparece el número
        self.assertNotEqual(five, six)    # y cambia con el total


class ConditionTests(PanelTestCase):
    def bar(self):
        return pygame.Rect(self.panel.left, BAR_Y, self.panel.w, BAR_H)

    def test_el_estado_arranca_en_verde(self):
        self.assertEqual(GameState().alert, "GREEN")
        self.assertEqual(ALERTS, ("GREEN", "YELLOW", "RED"))

    def test_la_condicion_es_una_barra_de_color_a_todo_el_ancho_con_el_nombre_dentro(self):
        for alert, color in CONDITION_COLORS.items():
            self.state.alert = alert
            self.draw()
            bar = self.bar()
            self.assertEqual(tuple(self.screen.get_at(bar.topleft))[:3], tuple(color)[:3], alert)
            self.assertEqual(tuple(self.screen.get_at((bar.right - 1, bar.bottom - 1)))[:3], tuple(color)[:3], alert)
            self.assertIn((0, 0, 0), colors(self.screen, bar), f"{alert}: falta el texto oscuro dentro de la barra")
            others = {tuple(c)[:3] for k, c in CONDITION_COLORS.items() if k != alert}
            self.assertFalse(others & colors(self.screen, bar), alert)

    def test_el_nombre_de_la_alerta_cambia_el_dibujo_de_la_barra(self):
        seen = set()
        for alert in ALERTS:
            self.state.alert = alert
            self.draw()
            seen.add(pygame.image.tobytes(self.screen.subsurface(self.bar()), "RGB"))
        self.assertEqual(len(seen), 3)

    def test_todo_nivel_empieza_en_verde(self):
        self.engine.state.alert = "RED"
        self.engine._apply_scene_change("PLAY")
        self.assertEqual(self.engine.state.alert, "GREEN")

    def test_una_partida_nueva_vuelve_a_verde(self):
        self.state.alert = "RED"
        self.state.reset()
        self.assertEqual(self.state.alert, "GREEN")


class LayoutTests(PanelTestCase):
    def test_el_panel_no_dibuja_dentro_del_campo_de_juego(self):
        self.state.lives, self.state.cheat, self.state.alert = 9, True, "YELLOW"
        self.draw()
        world = esper.World()
        world.create_entity(CTransform(pygame.Vector2(512, 512)), CMinimapTrack("player"))
        system_minimap_rendering(world, self.screen, CFG, WORLD, pygame.Vector2(512, 512), 0.0)
        self.assertFalse(lit(self.screen, pygame.Rect(0, 0, self.engine.viewport.w, 208)), "el panel invade el campo de juego")

    def test_las_filas_van_en_orden_sin_encimarse_y_caben_en_pantalla(self):
        radar = radar_rect(CFG)
        order = [ROWS["hi_label"] + 8, ROWS["hi_value"] + 8, ROWS["up_label"] + 8, ROWS["up_value"] + 8,
                 ROWS["cheat"] + 8, ROWS["condition"] + 8, BAR_Y + BAR_H, radar.top, radar.bottom,
                 ICONS_Y + self.icon_size[1], ROWS["round"] + 8]
        self.assertEqual(order, sorted(order), "las filas se encaraman")
        for earlier, later in zip(
                [ROWS["hi_label"], ROWS["hi_value"], ROWS["up_label"], ROWS["up_value"], ROWS["cheat"], ROWS["condition"], BAR_Y, radar.top, radar.bottom, ICONS_Y],
                [ROWS["hi_value"], ROWS["up_label"], ROWS["up_value"], ROWS["cheat"], ROWS["condition"], BAR_Y, radar.top, radar.bottom, ICONS_Y, ROWS["round"]]):
            self.assertLessEqual(earlier, later)
        self.assertLessEqual(ROWS["round"] + 8, 208)
        self.assertEqual((radar.left, radar.right), (self.panel.left, self.panel.right))

    def test_el_radar_es_mas_alto_que_ancho_y_mas_grande_que_el_minimapa_original_del_proyecto(self):
        radar = radar_rect(CFG)
        self.assertGreater(radar.height, radar.width)
        self.assertGreater(radar.width * radar.height, 64 * 64)

    def test_el_aviso_cheat_va_entre_el_puntaje_y_condition(self):
        self.state.cheat = True
        self.draw()
        cheat = self.row("cheat")
        self.assertIn(tuple(RED)[:3], colors(self.screen, cheat))
        self.assertGreater(cheat.top, ROWS["up_value"] + 7)
        self.assertLess(cheat.bottom, ROWS["condition"] + 1)


class RadarMathTests(unittest.TestCase):
    """Radar centrado en la nave (ver s_minimap)."""

    RECT = radar_rect(CFG)
    SCALE = CFG["scale"]

    def point(self, pos, center=(500, 400)):
        return radar_point(pygame.Vector2(pos), pygame.Vector2(center), WORLD, self.RECT, self.SCALE)

    def test_el_centro_del_radar_es_la_nave(self):
        self.assertEqual(self.point((500, 400)), self.RECT.center)

    def test_el_radar_alcanza_mas_que_la_pantalla_de_juego(self):
        self.assertGreater(self.RECT.w * self.SCALE, 192)
        self.assertGreater(self.RECT.h * self.SCALE, 208)


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
        far = self.render([("base", (512 + 400, 512))])
        self.assertEqual(pygame.image.tobytes(far.subsurface(rect), "RGB"),
                         pygame.image.tobytes(before.subsurface(rect), "RGB"))

    def test_una_base_al_otro_lado_del_borde_del_mundo_se_ve_cerca_de_la_nave(self):
        screen = self.render([("base", (10, 512))], center=(1000, 512))
        self.assertIn((255, 64, 64), colors(screen, radar_rect(CFG)))

    def test_el_radar_sigue_el_centro_se_mueve_con_la_nave(self):
        base = ("base", (700, 512))
        a = self.render([base], center=(512, 512)).copy()
        b = self.render([base], center=(600, 512))
        self.assertNotEqual(pygame.image.tobytes(a, "RGB"), pygame.image.tobytes(b, "RGB"))

    def test_nada_se_dibuja_fuera_del_radar_aunque_la_marca_este_en_el_borde(self):
        rect = radar_rect(CFG)
        edge = (512 + (rect.w // 2 - 3) * CFG["scale"], 512)
        screen = self.render([("base", edge)])
        self.assertFalse(lit(screen, pygame.Rect(rect.left - 8, rect.top, 8, rect.height)))  # el campo de juego sigue vacío


class PlaySceneIntegrationTests(PanelTestCase):
    def test_el_nivel_dibuja_panel_y_radar_sin_fallar_y_cambia_con_la_alerta(self):
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.blast_left = 0
        scene.do_update(1 / 60)
        self.engine._draw()
        green = pygame.image.tobytes(self.engine.screen, "RGB")
        self.engine.state.alert = "RED"
        self.engine._draw()
        self.assertNotEqual(green, pygame.image.tobytes(self.engine.screen, "RGB"))

    def test_en_pausa_desaparecen_las_marcas_del_radar_pero_queda_el_radar_y_la_barra(self):
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.blast_left = 0
        self.engine._draw()
        radar = radar_rect(CFG)
        self.assertGreater(len(colors(self.engine.screen, radar)), 1)  # con marcas: fondo, bases, nave...
        scene.paused = True
        self.engine._draw()
        self.assertEqual(colors(self.engine.screen, radar), {tuple(color_from_cfg(CFG["bg_color"]))[:3]})
        self.assertTrue(lit(self.engine.screen, pygame.Rect(self.panel.left, 0, self.panel.w, 32)))


if __name__ == "__main__":
    unittest.main()
