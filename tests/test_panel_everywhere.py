"""La barra lateral es parte fija de la pantalla del juego: está desde el inicio y en todas las
pantallas (salvo el editor, que tiene su propio panel), y las escenas solo usan el campo de juego."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.ecs.components.c_star import CStar
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_minimap import radar_rect
from src.engine.data_loader import load_json
from src.engine.game_engine import GameEngine
from src.engine.service_locator import color_from_cfg

CFG = load_json("assets/cfg/world.json")["minimap"]
MENU = load_json("assets/cfg/menu.json")
STORY = load_json("assets/cfg/story.json")
STAGE_LETTERS = 22  # 176 px de campo de juego / 8 px por letra
SCENES_WITH_PANEL = ("INTRO", "TITLE", "INSTRUCTIONS", "CREDITS", "CUTSCENE", "VICTORY", "DEFEAT",
                     "RECORD", "ATTRACT_INFO", "PLAY", "ATTRACT")


def panel_bytes(screen: pygame.Surface, engine: GameEngine) -> bytes:
    rect = pygame.Rect(engine.viewport.right, 0, screen.get_width() - engine.viewport.right, screen.get_height())
    return pygame.image.tobytes(screen.subsurface(rect), "RGB")


def lit(surface, rect):
    return any(surface.get_at((x, y))[:3] != (0, 0, 0) for x in range(rect.left, rect.right)
               for y in range(rect.top, rect.bottom))


class PanelEverywhereTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine.state.add_score(1250)

    def open(self, name, seconds=0.5):
        self.engine._apply_scene_change(name)
        scene = self.engine._current_scene
        for _ in range(round(seconds * 60)):
            scene.do_update(1 / 60)
            if self.engine._next_scene is not None:
                break
        self.engine._next_scene = None
        self.engine._draw()
        return scene

    def test_el_juego_arranca_en_una_pantalla_con_barra(self):
        self.assertEqual(self.engine.cfg_scenes["start_scene"], "INTRO")
        scene = self.open(self.engine.cfg_scenes["start_scene"])
        self.assertTrue(scene.has_panel)
        self.assertTrue(lit(self.engine.screen, pygame.Rect(176, 0, 80, 54)))  # HI-SCORE y 1UP

    def test_todas_las_pantallas_tienen_barra_menos_el_editor(self):
        for name, cls in GameEngine.SCENES.items():
            self.assertEqual(cls.has_panel, name != "EDITOR", name)

    def test_la_barra_es_identica_en_todas_las_pantallas_que_no_son_el_nivel(self):
        """Mismo estado de partida => misma barra, con el radar vacío, sin que se cuele nada de la escena."""
        reference = None
        for name in ("INTRO", "TITLE", "INSTRUCTIONS", "CREDITS", "CUTSCENE", "VICTORY", "DEFEAT", "RECORD", "ATTRACT_INFO"):
            self.open(name)
            current = panel_bytes(self.engine.screen, self.engine)
            reference = reference or current
            self.assertEqual(current, reference, f"la barra de {name} es distinta")

    def test_todas_muestran_hi_score_puntaje_radar_condition_vidas_y_ronda(self):
        for name in SCENES_WITH_PANEL:
            self.open(name)
            screen = self.engine.screen
            rect = radar_rect(CFG)
            self.assertEqual(tuple(screen.get_at(rect.topleft))[:3], tuple(color_from_cfg(CFG["border_color"]))[:3], name)
            for label, area in (("HI-SCORE/1UP", pygame.Rect(176, 0, 80, 54)), ("CONDITION", pygame.Rect(176, 138, 80, 18)),
                                ("vidas", pygame.Rect(176, 165, 80, 17)), ("ROUND", pygame.Rect(176, 188, 80, 10))):
                self.assertTrue(lit(screen, area), f"{name}: falta {label}")

    def test_el_puntaje_y_las_vidas_se_ven_tambien_fuera_del_nivel(self):
        self.engine.state.lives = 2
        self.open("TITLE")
        two = panel_bytes(self.engine.screen, self.engine)
        self.engine.state.lives = 4
        self.open("TITLE")
        self.assertNotEqual(two, panel_bytes(self.engine.screen, self.engine))

    def test_el_modo_trampa_se_avisa_en_cualquier_pantalla(self):
        self.engine.state.cheat = True
        for name in ("TITLE", "INSTRUCTIONS", "DEFEAT"):
            self.open(name)
            self.assertTrue(lit(self.engine.screen, pygame.Rect(176, 155, 80, 9)), name)

    def test_el_editor_usa_toda_la_pantalla_sin_la_barra_del_juego(self):
        self.open("EDITOR", 0.1)
        self.assertFalse(self.engine._current_scene.has_panel)
        self.assertTrue(lit(self.engine.screen, pygame.Rect(184, 20, 72, 100)))

    def test_el_motor_deja_el_recorte_de_pantalla_completo_tras_dibujar(self):
        for name in ("TITLE", "PLAY", "EDITOR"):
            self.open(name, 0.1)
            self.assertEqual(self.engine.screen.get_clip(), self.engine.screen.get_rect(), name)


class StageLayoutTests(unittest.TestCase):
    """Las escenas se dibujan solo en el campo de juego (176 px): nada se corta bajo la barra."""

    def setUp(self):
        self.engine = GameEngine()

    def test_los_textos_de_los_menus_caben_en_el_campo_de_juego(self):
        for key in ("instructions", "credits", "victory", "defeat", "record"):
            for line in MENU[key]["lines"] + [MENU[key]["title"]]:
                self.assertLessEqual(len(line), STAGE_LETTERS, f"{key}: «{line}»")
        for line in MENU["exit_confirm"]:
            self.assertLessEqual(len(line), STAGE_LETTERS, line)
        self.assertLessEqual(len(MENU["attract"]["hint"]), STAGE_LETTERS)
        for item in MENU["title_items"]:
            self.assertLessEqual(len("> " + item["label"]), STAGE_LETTERS, item["label"])

    def test_los_textos_de_las_escenas_de_historia_caben(self):
        for name in ("intro", "cutscene"):
            for event in STORY[name]["events"]:
                if event["type"] == "text":
                    self.assertLessEqual(len(event["text"].format(round=10)), STAGE_LETTERS, event["text"])

    def test_la_animacion_esta_centrada_en_el_campo_y_no_en_la_pantalla(self):
        """Ningún evento de historia usa el centro de la pantalla completa (x=128)."""
        for name in ("intro", "cutscene"):
            for event in STORY[name]["events"]:
                for point in (event.get("pos"), event.get("to")):
                    if point and event["type"] in ("text", "image"):
                        self.assertEqual(point["x"], self.engine.viewport.centerx, f"{name}: {event.get('text', event['type'])}")

    def test_las_estrellas_de_los_menus_nacen_en_el_campo_de_juego(self):
        for name in ("TITLE", "INTRO", "CUTSCENE", "INSTRUCTIONS", "VICTORY"):
            self.engine._apply_scene_change(name)
            scene = self.engine._current_scene
            xs = [t.pos.x for _, (t, _s) in scene.world.get_components(CTransform, CStar)]
            self.assertTrue(xs, name)
            self.assertLess(max(xs), self.engine.viewport.right, name)

    def centered(self, name, rows, color_key="title"):
        """Centro horizontal de los píxeles del color del título en las filas `rows`."""
        self.engine._apply_scene_change(name)
        self.engine._current_scene.do_update(0.1)
        self.engine._draw()
        color = tuple(color_from_cfg(MENU["colors"][color_key]))[:3]
        xs = [x for y in rows for x in range(176) if tuple(self.engine.screen.get_at((x, y)))[:3] == color]
        self.assertTrue(xs, name)
        return (min(xs) + max(xs)) / 2

    def test_los_titulos_de_las_pantallas_de_informacion_estan_centrados_en_el_campo(self):
        for name in ("INSTRUCTIONS", "CREDITS", "VICTORY", "DEFEAT", "RECORD"):
            self.assertAlmostEqual(self.centered(name, range(20, 28)), 88, delta=5, msg=name)

    def test_el_menu_del_titulo_esta_centrado_en_el_campo(self):
        self.assertAlmostEqual(self.centered("TITLE", range(125, 134), "selected"), 88, delta=10)

    def test_el_hint_de_derrota_esta_centrado_en_el_campo(self):
        self.assertAlmostEqual(self.centered("DEFEAT", range(172, 180), "selected"), 88, delta=6)

    def test_todo_se_dibuja_sin_fallar_durante_toda_la_animacion(self):
        for name in ("INTRO", "CUTSCENE"):
            self.engine._apply_scene_change(name)
            scene = self.engine._current_scene
            for _ in range(round(STORY[name.lower()]["duration"] * 60)):
                scene.do_update(1 / 60)
                self.engine._draw()
                if self.engine._next_scene is not None:
                    break


if __name__ == "__main__":
    unittest.main()
