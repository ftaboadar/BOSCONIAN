"""Pruebas de la persiana entre pantallas (#90): bandas verde menta que cubren el campo de juego,
se cambia de escena con el campo cubierto y se abren; la barra lateral no se mueve."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine.data_loader import ConfigError, load_json
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.scenes.story_scenes import CutsceneScene
from src.engine.scenes.title_scene import TitleScene
from src.engine.shutter import Shutter

CFG = load_json("assets/cfg/world.json")["shutter"]
STAGE = pygame.Rect(0, 0, 192, 208)
MINT = tuple(pygame.Color(CFG["color"]["r"], CFG["color"]["g"], CFG["color"]["b"]))[:3]
DT = 1 / 60


def shutter():
    return Shutter(CFG, STAGE)


class ShutterModelTests(unittest.TestCase):
    def test_empieza_abierta_y_sin_hacer_nada(self):
        s = shutter()
        self.assertEqual((s.cover, s.busy, s.closing), (0.0, False, False))
        screen = pygame.Surface((256, 208)); screen.fill((0, 0, 0))
        s.draw(screen)
        self.assertEqual(pygame.image.tobytes(screen, "RGB"), bytes(256 * 208 * 3))

    def test_solo_algunas_escenas_llevan_persiana(self):
        s = shutter()
        for name in CFG["to"]:
            self.assertTrue(s.wants(name))
        for name in ("TITLE", "INSTRUCTIONS", "CREDITS", "VICTORY", "DEFEAT", "EDITOR"):
            self.assertFalse(s.wants(name), name)

    def test_al_cerrarse_cubre_de_a_poco_hasta_cerrar_del_todo(self):
        s = shutter()
        self.assertTrue(s.close("PLAY"))
        covers = []
        closed_at = None
        for i in range(round(CFG["close_seconds"] / DT) + 5):
            done = s.update(DT)
            covers.append(s.cover)
            if done:
                closed_at = i
                break
        self.assertEqual(covers, sorted(covers))                 # nunca retrocede
        self.assertAlmostEqual(covers[len(covers) // 2], 0.5, delta=0.1)
        self.assertEqual(s.cover, 1.0)
        self.assertAlmostEqual((closed_at + 1) * DT, CFG["close_seconds"], delta=2 * DT)
        self.assertFalse(s.closing)
        self.assertTrue(s.busy)

    def test_avisa_de_que_esta_cerrada_una_sola_vez(self):
        s = shutter(); s.close("PLAY")
        signals = [s.update(DT) for _ in range(round(CFG["close_seconds"] / DT) + 30)]
        self.assertEqual(signals.count(True), 1)

    def test_al_abrirse_descubre_y_queda_libre(self):
        s = shutter(); s.close("PLAY")
        while not s.update(DT):
            pass
        s.open()
        self.assertEqual(s.cover, 1.0)
        previous = 1.0
        for _ in range(round(CFG["open_seconds"] / DT) + 3):
            s.update(DT)
            self.assertLessEqual(s.cover, previous)
            previous = s.cover
        self.assertEqual((s.cover, s.busy, s.target), (0.0, False, None))

    def test_no_se_apilan_persianas(self):
        s = shutter()
        self.assertTrue(s.close("PLAY"))
        self.assertFalse(s.close("CUTSCENE"))
        self.assertEqual(s.target, "PLAY")

    def test_bandas_a_medio_cerrar_dejan_una_franja_negra_en_el_centro(self):
        s = shutter(); s.close("PLAY")
        while s.cover < 0.5:
            s.update(DT)
        screen = pygame.Surface((256, 208)); screen.fill((0, 0, 0))
        s.draw(screen)
        band = round(104 * s.cover)
        self.assertEqual(tuple(screen.get_at((50, 0)))[:3], MINT)                 # arriba
        self.assertEqual(tuple(screen.get_at((50, band - 1)))[:3], MINT)
        self.assertEqual(tuple(screen.get_at((50, 207)))[:3], MINT)               # abajo
        self.assertEqual(tuple(screen.get_at((50, 208 - band)))[:3], MINT)
        self.assertEqual(tuple(screen.get_at((50, 104)))[:3], (0, 0, 0))          # el centro sigue visible

    def test_cerrada_cubre_todo_el_campo_pero_no_la_barra(self):
        s = shutter(); s.close("PLAY")
        while not s.update(DT):
            pass
        screen = pygame.Surface((256, 208)); screen.fill((9, 9, 9))
        s.draw(screen)
        for point in ((0, 0), (191, 0), (0, 207), (191, 207), (96, 104)):
            self.assertEqual(tuple(screen.get_at(point))[:3], MINT, point)
        for point in ((192, 0), (255, 104), (230, 207)):
            self.assertEqual(tuple(screen.get_at(point))[:3], (9, 9, 9), point)  # la barra queda intacta

    def test_configuracion_invalida_falla(self):
        for bad in ({"close_seconds": 0}, {"open_seconds": -1}):
            with self.assertRaises(ConfigError):
                Shutter({**CFG, **bad}, STAGE)
        for key in CFG:
            with self.assertRaises(ConfigError, msg=key):
                Shutter({k: v for k, v in CFG.items() if k != key}, STAGE)


class EngineShutterTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine.delta_time = DT
        self.engine._apply_scene_change("TITLE")
        self.title = self.engine._current_scene

    def frames(self, seconds):
        for _ in range(round(seconds / DT)):
            self.engine._frame()

    def test_jugar_cierra_la_persiana_y_la_escena_sigue_siendo_el_titulo_hasta_cubrir(self):
        self.engine.switch_scene("CUTSCENE")
        self.engine._frame()
        self.assertIsInstance(self.engine._current_scene, TitleScene)
        self.assertTrue(self.engine.shutter.closing)
        self.assertIsNone(self.engine._next_scene)  # el pedido quedó en la persiana

    def test_con_el_campo_cubierto_se_cambia_de_escena_y_luego_se_abre(self):
        self.engine.switch_scene("CUTSCENE")
        self.frames(CFG["close_seconds"] + 3 * DT)
        self.assertIsInstance(self.engine._current_scene, CutsceneScene)
        self.assertEqual(self.engine.shutter.state, "opening")
        self.frames(CFG["open_seconds"] + 3 * DT)
        self.assertFalse(self.engine.shutter.busy)

    def test_en_el_momento_del_cambio_el_campo_esta_todo_cubierto(self):
        self.engine.switch_scene("CUTSCENE")
        for _ in range(round(CFG["close_seconds"] / DT) + 5):
            self.engine._frame()
            if isinstance(self.engine._current_scene, CutsceneScene):
                break
        stage = self.engine.screen.subsurface(self.engine.viewport)
        self.assertEqual({tuple(stage.get_at((x, y)))[:3] for x in (0, 95, 191) for y in (0, 104, 207)}, {MINT})

    def test_la_escena_se_congela_mientras_la_persiana_se_cierra(self):
        self.engine.switch_scene("CUTSCENE")
        self.engine._frame()
        idle = self.title.idle
        self.frames(CFG["close_seconds"] / 2)
        self.assertEqual(self.title.idle, idle)

    def test_no_se_aceptan_teclas_mientras_se_cierra(self):
        self.engine.switch_scene("CUTSCENE")
        self.engine._frame()
        selected = self.title.menu.selected
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        self.engine._frame()
        self.assertEqual(self.title.menu.selected, selected)

    def test_la_barra_lateral_no_se_mueve_durante_la_persiana(self):
        self.engine._draw()
        panel = self.engine.hud.panel
        before = pygame.image.tobytes(self.engine.screen.subsurface(panel), "RGB")
        self.engine.switch_scene("CUTSCENE")
        for _ in range(round((CFG["close_seconds"] + CFG["open_seconds"]) / DT)):
            self.engine._frame()
            self.assertEqual(pygame.image.tobytes(self.engine.screen.subsurface(panel), "RGB"), before)

    def test_una_escena_sin_persiana_cambia_de_inmediato(self):
        self.engine.switch_scene("INSTRUCTIONS")
        self.engine._frame()
        self.assertEqual(type(self.engine._current_scene).__name__, "InstructionsScene")
        self.assertFalse(self.engine.shutter.busy)

    def test_un_pedido_durante_la_apertura_se_aplica_sin_apilar_persianas(self):
        self.engine.switch_scene("CUTSCENE")
        self.frames(CFG["close_seconds"] + 3 * DT)
        self.assertEqual(self.engine.shutter.state, "opening")
        self.engine.switch_scene("PLAY")
        self.engine._frame()
        self.assertEqual(type(self.engine._current_scene).__name__, "PlayScene")
        self.assertNotEqual(self.engine.shutter.state, "closing")

    def test_cada_nivel_y_cada_vida_llevan_persiana_al_volver_al_juego(self):
        self.engine._apply_scene_change("PLAY")
        self.engine.switch_scene("PLAY")  # morir o pasar de nivel
        self.engine._frame()
        self.assertTrue(self.engine.shutter.closing)

    def test_el_editor_no_usa_persiana_al_entrar_pero_si_al_volver_al_juego(self):
        self.engine.switch_scene("EDITOR")
        self.engine._frame()
        self.assertEqual(type(self.engine._current_scene).__name__, "EditorScene")
        self.engine.switch_scene("PLAY")
        self.engine._frame()
        self.assertTrue(self.engine.shutter.closing)

    def test_cerrar_la_ventana_funciona_aunque_haya_persiana(self):
        self.engine.is_running = True
        self.engine.switch_scene("CUTSCENE")
        self.engine._frame()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        self.engine._frame()
        self.assertFalse(self.engine.is_running)


class TitleFireTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("TITLE")
        self.title = self.engine._current_scene

    def test_disparar_en_el_titulo_empieza_la_partida_como_enter(self):
        self.engine.state.add_score(500)
        self.title.do_action("FIRE", Phase.START)
        self.assertEqual(self.engine._next_scene, "CUTSCENE")
        self.assertEqual(self.engine.state.score, 0)  # start_game reinició la partida

    def test_disparar_sobre_otra_opcion_hace_lo_que_haria_enter(self):
        self.title.do_action("DOWN", Phase.START)
        self.title.do_action("DOWN", Phase.START)
        self.title.do_action("FIRE", Phase.START)
        self.assertEqual(self.engine._next_scene, "INSTRUCTIONS")

    def test_soltar_la_tecla_de_disparo_no_hace_nada(self):
        self.title.do_action("FIRE", Phase.END)
        self.assertIsNone(self.engine._next_scene)


if __name__ == "__main__":
    unittest.main()
