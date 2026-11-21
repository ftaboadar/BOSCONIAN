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
from src.engine.hud import BAR_H, BAR_Y, ICONS_Y, ROWS
from src.engine.game_engine import GameEngine
from src.engine.service_locator import color_from_cfg

CFG = load_json("assets/cfg/world.json")["minimap"]
MENU = load_json("assets/cfg/menu.json")
STORY = load_json("assets/cfg/story.json")
STAGE_LETTERS = 24  # 192 px de campo de juego / 8 px por letra
SCENES_WITH_PANEL = ("INTRO", "TITLE", "INSTRUCTIONS", "CREDITS", "CUTSCENE", "VICTORY", "DEFEAT",
                     "RECORD", "ATTRACT_INFO", "PLAY", "ATTRACT")


def panel_bytes(screen: pygame.Surface, engine: GameEngine) -> bytes:
    return pygame.image.tobytes(screen.subsurface(engine.hud.panel), "RGB")


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
        panel = self.engine.hud.panel
        self.assertTrue(lit(self.engine.screen, pygame.Rect(panel.left, 0, panel.w, 32)))  # HI-SCORE y 1UP

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
            screen, panel = self.engine.screen, self.engine.hud.panel
            radar = radar_rect(CFG)
            self.assertEqual(tuple(screen.get_at(radar.topleft))[:3], tuple(color_from_cfg(CFG["bg_color"]))[:3], name)
            icons = pygame.Rect(panel.left, ICONS_Y, panel.w, 17)
            for label, area in (("HI-SCORE/1UP", pygame.Rect(panel.left, 0, panel.w, 32)),
                                ("CONDITION", pygame.Rect(panel.left, BAR_Y, panel.w, BAR_H)),
                                ("vidas", icons), ("ROUND", pygame.Rect(panel.left, ROWS["round"], panel.w, 8))):
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
            panel = self.engine.hud.panel
            self.assertTrue(lit(self.engine.screen, pygame.Rect(panel.left, ROWS["cheat"], panel.w, 8)), name)

    def test_el_editor_usa_toda_la_pantalla_sin_la_barra_del_juego(self):
        self.open("EDITOR", 0.1)
        self.assertFalse(self.engine._current_scene.has_panel)
        self.assertTrue(lit(self.engine.screen, pygame.Rect(184, 20, 72, 100)))

    def test_el_motor_deja_el_recorte_de_pantalla_completo_tras_dibujar(self):
        for name in ("TITLE", "PLAY", "EDITOR"):
            self.open(name, 0.1)
            self.assertEqual(self.engine.screen.get_clip(), self.engine.screen.get_rect(), name)


class StageLayoutTests(unittest.TestCase):
    """Las escenas se dibujan solo en el campo de juego (192 px): nada se corta bajo la barra."""

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

    LOGO_MARGIN = 8  # px libres a cada lado del logo

    def logo_surface(self, name):
        from src.ecs.components.c_surface import CSurface
        self.engine._apply_scene_change(name)
        scene = self.engine._current_scene
        if name == "INTRO":
            scene.do_update(0.5)  # el logo es el primer evento
        surfs = [c.surf for _, c in scene.world.get_component(CSurface)]
        return max(surfs, key=lambda surf: surf.get_width())

    def test_el_logo_del_titulo_deja_margen_a_los_lados(self):
        surf = self.logo_surface("TITLE")
        self.assertEqual(surf.get_width(), MENU["logo_width"])
        self.assertLessEqual(surf.get_width(), self.engine.viewport.w - 2 * self.LOGO_MARGIN)

    def test_el_logo_conserva_su_proporcion(self):
        from src.engine.service_locator import ServiceLocator
        full = ServiceLocator.images.get("title")
        surf = self.logo_surface("TITLE")
        self.assertAlmostEqual(surf.get_height() / surf.get_width(), full.get_height() / full.get_width(), delta=0.02)

    def test_el_intro_usa_el_mismo_logo_reducido(self):
        self.assertEqual(self.logo_surface("INTRO").get_width(), MENU["logo_width"])

    def test_el_logo_ya_no_roza_los_bordes_del_campo(self):
        """Los píxeles del logo (cian) dejan libre una franja a ambos lados del campo de juego."""
        self.engine._apply_scene_change("TITLE")
        self.engine._current_scene.do_update(0.1)
        self.engine._draw()
        screen = self.engine.screen
        cyan = [x for y in range(30, 110) for x in range(self.engine.viewport.w)
                if screen.get_at((x, y))[1] > 200 and screen.get_at((x, y))[2] > 200 and screen.get_at((x, y))[0] < 60]
        self.assertTrue(cyan)
        self.assertGreaterEqual(min(cyan), self.LOGO_MARGIN - 2)
        self.assertLessEqual(max(cyan), self.engine.viewport.w - self.LOGO_MARGIN + 2)

    def centered(self, name, rows, color_key="title"):
        """Centro horizontal de los píxeles del color del título en las filas `rows`."""
        self.engine._apply_scene_change(name)
        self.engine._current_scene.do_update(0.1)
        self.engine._draw()
        color = tuple(color_from_cfg(MENU["colors"][color_key]))[:3]
        xs = [x for y in rows for x in range(self.engine.viewport.w) if tuple(self.engine.screen.get_at((x, y)))[:3] == color]
        self.assertTrue(xs, name)
        return (min(xs) + max(xs)) / 2

    def test_los_titulos_de_las_pantallas_de_informacion_estan_centrados_en_el_campo(self):
        for name in ("INSTRUCTIONS", "CREDITS", "VICTORY", "DEFEAT", "RECORD"):
            self.assertAlmostEqual(self.centered(name, range(20, 28)), self.engine.viewport.centerx, delta=5, msg=name)

    def test_el_menu_del_titulo_esta_centrado_en_el_campo(self):
        self.assertAlmostEqual(self.centered("TITLE", range(125, 134), "selected"), self.engine.viewport.centerx, delta=10)

    def test_el_hint_de_derrota_esta_centrado_en_el_campo(self):
        self.assertAlmostEqual(self.centered("DEFEAT", range(172, 180), "selected"), self.engine.viewport.centerx, delta=6)

    def test_todo_se_dibuja_sin_fallar_durante_toda_la_animacion(self):
        for name in ("INTRO", "CUTSCENE"):
            self.engine._apply_scene_change(name)
            scene = self.engine._current_scene
            for _ in range(round(STORY[name.lower()]["duration"] * 60)):
                scene.do_update(1 / 60)
                self.engine._draw()
                if self.engine._next_scene is not None:
                    break


class ScaledImageTests(unittest.TestCase):
    def setUp(self):
        GameEngine()

    def test_scaled_to_width_conserva_proporcion_y_transparencia(self):
        from src.create.prefab_creator import scaled_to_width
        surf = pygame.Surface((100, 40), pygame.SRCALPHA)
        surf.fill((255, 0, 0, 255))
        out = scaled_to_width(surf, 50)
        self.assertEqual(out.get_size(), (50, 20))
        self.assertEqual(out.get_at((25, 10)).a, 255)
        self.assertEqual(scaled_to_width(pygame.Surface((100, 1)), 10).get_height(), 1)  # nunca 0 de alto

    def test_create_image_sin_ancho_no_cambia_la_imagen(self):
        import esper
        from src.create.prefab_creator import create_image
        from src.ecs.components.c_surface import CSurface
        from src.engine.service_locator import ServiceLocator
        world = esper.World()
        ent = create_image(world, "title", pygame.Vector2(10, 10))
        self.assertIs(world.component_for_entity(ent, CSurface).surf, ServiceLocator.images.get("title"))
        ent = create_image(world, "title", pygame.Vector2(10, 10), 100)
        self.assertEqual(world.component_for_entity(ent, CSurface).surf.get_width(), 100)


if __name__ == "__main__":
    unittest.main()
