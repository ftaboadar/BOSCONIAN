"""Pruebas del modo editor de niveles (#44): entrar y salir en el juego, cargar y guardar
niveles, colocar bases (rotadas o no) y el inicio de la nave, y las opciones del nivel."""

import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.ecs.components.c_minimap_track import CMinimapTrack
from src.engine import data_loader
from src.engine.data_loader import ConfigError, format_level, level_numbers, load_json, load_level, save_level
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.level_editor import MAX_BASES, STEP, LevelEditor
from src.engine.level_flow import after_level_cleared

WORLD = pygame.Vector2(1024, 1024)
TRACKS = [t for t in load_json("assets/cfg/resources.json")["music"] if t != "title"]


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class TempLevels(unittest.TestCase):
    """Cada prueba trabaja sobre una copia de assets/cfg/levels en un directorio temporal."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = os.path.join(tmp.name, "levels")
        shutil.copytree(data_loader.LEVELS_DIR, self.dir)
        patcher = mock.patch.object(data_loader, "LEVELS_DIR", self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)


class FormatTests(TempLevels):
    def test_los_niveles_del_proyecto_se_reescriben_con_los_mismos_datos(self):
        for n in level_numbers():
            level = load_level(n)
            save_level(n, level)
            self.assertEqual(load_level(n), level, n)

    def test_el_formato_es_el_de_los_archivos_existentes(self):
        text = format_level(load_level(3))
        self.assertIn('"player_start": { "x": 512, "y": 512 },', text)
        self.assertIn('{ "x": 170, "y": 710, "orientation": "horizontal" }', text)
        self.assertTrue(text.endswith("}\n"))
        json.loads(text)

    def test_guardar_un_nivel_invalido_falla_y_no_toca_el_archivo(self):
        before = read(data_loader.level_path(2))
        bad = load_level(2)
        bad["bases"].append({"x": 1, "y": 1, "orientation": "diagonal"})
        with self.assertRaises(ConfigError):
            save_level(2, bad)
        self.assertEqual(read(data_loader.level_path(2)), before)
        self.assertFalse(any(f.endswith(".tmp") for f in os.listdir(self.dir)))

    def test_guardar_un_numero_nuevo_crea_el_archivo(self):
        level = load_level(1)
        save_level(11, level)
        self.assertIn(11, level_numbers())


class EditorModelTests(TempLevels):
    def editor(self, number=1):
        return LevelEditor(WORLD, TRACKS, number)

    def move_to(self, ed, x, y):
        ed.cursor = pygame.Vector2(x, y)

    def test_carga_el_nivel_pedido(self):
        ed = self.editor(3)
        self.assertEqual(len(ed.level["bases"]), 4)
        self.assertEqual(ed.level["difficulty"], 2)
        self.assertFalse(ed.dirty)

    def test_el_cursor_se_mueve_de_a_un_paso_y_no_sale_del_mundo(self):
        ed = self.editor()
        start = pygame.Vector2(ed.cursor)
        ed.move_cursor(1, 0)
        self.assertEqual(ed.cursor, start + pygame.Vector2(STEP, 0))
        for _ in range(200):
            ed.move_cursor(-1, -1)
        self.assertEqual((ed.cursor.x, ed.cursor.y), (0, 0))
        for _ in range(200):
            ed.move_cursor(1, 1)
        self.assertEqual((ed.cursor.x, ed.cursor.y), (WORLD.x - 1, WORLD.y - 1))

    def test_la_base_horizontal_es_la_vertical_girada(self):
        ed = self.editor()
        v = ed.footprint({"x": 100, "y": 100, "orientation": "vertical"})
        h = ed.footprint({"x": 100, "y": 100, "orientation": "horizontal"})
        self.assertEqual((v.w, v.h), (h.h, h.w))
        self.assertEqual(v.center, h.center)

    def test_poner_una_base_con_cada_orientacion(self):
        ed = self.editor()
        before = len(ed.level["bases"])
        self.move_to(ed, 900, 900)
        self.assertEqual(ed.place_base(), "BASE PUESTA")
        self.move_to(ed, 900, 700)
        ed.rotate()  # sin base bajo el cursor: cambia la orientación de las nuevas
        ed.place_base()
        bases = ed.level["bases"]
        self.assertEqual(len(bases), before + 2)
        self.assertEqual((bases[-2]["orientation"], bases[-1]["orientation"]), ("vertical", "horizontal"))
        self.assertTrue(ed.dirty)

    def test_no_se_pone_una_base_encima_de_otra(self):
        ed = self.editor(3)
        base = ed.level["bases"][0]
        self.move_to(ed, base["x"] + 10, base["y"] + 10)
        self.assertEqual(ed.place_base(), "OCUPADO")
        self.assertEqual(len(ed.level["bases"]), 4)

    def test_no_se_pone_una_base_sobre_el_inicio_de_la_nave(self):
        ed = self.editor()
        self.move_to(ed, ed.start_pos.x + 4, ed.start_pos.y)
        self.assertEqual(ed.place_base(), "ES EL INICIO")

    def test_hay_un_maximo_de_bases(self):
        ed = self.editor()
        ed.level["bases"] = []
        spots = [(x, y) for y in (100, 300, 500, 700, 900) for x in (100, 300, 500, 700, 900)]
        placed = 0
        for x, y in spots:
            self.move_to(ed, x, y)
            if ed.place_base() == "BASE PUESTA":
                placed += 1
        self.assertEqual(len(ed.level["bases"]), MAX_BASES)
        self.assertEqual(placed, MAX_BASES)

    def test_borrar_la_base_bajo_el_cursor(self):
        ed = self.editor(3)
        base = ed.level["bases"][1]
        self.move_to(ed, base["x"], base["y"])
        self.assertEqual(ed.delete_base(), "BASE BORRADA")
        self.assertNotIn(base, ed.level["bases"])
        self.assertEqual(ed.delete_base(), "NO HAY BASE")

    def test_girar_una_base_existente(self):
        ed = self.editor(3)
        base = ed.level["bases"][1]
        was = base["orientation"]
        self.move_to(ed, base["x"], base["y"])
        ed.rotate()
        self.assertNotEqual(base["orientation"], was)
        ed.rotate()
        self.assertEqual(base["orientation"], was)

    def test_no_se_gira_una_base_si_la_girada_chocaria_con_otra(self):
        ed = self.editor()
        ed.level["bases"] = [{"x": 300, "y": 300, "orientation": "vertical"},
                             {"x": 300, "y": 363, "orientation": "vertical"}]  # 1 px de margen
        self.move_to(ed, 300, 300)
        self.assertEqual(ed.rotate(), "OCUPADO")
        self.assertEqual(ed.level["bases"][0]["orientation"], "vertical")

    def test_poner_el_inicio_de_la_nave(self):
        ed = self.editor()
        self.move_to(ed, 800, 800)
        self.assertEqual(ed.set_start(), "INICIO PUESTO")
        self.assertEqual(ed.level["player_start"], {"x": 800, "y": 800})

    def test_el_inicio_no_puede_estar_dentro_de_una_base(self):
        ed = self.editor(3)
        base = ed.level["bases"][0]
        old = dict(ed.level["player_start"])
        self.move_to(ed, base["x"], base["y"])
        self.assertEqual(ed.set_start(), "OCUPADO")
        self.assertEqual(ed.level["player_start"], old)

    def test_la_dificultad_recorre_los_valores_definidos_y_da_la_vuelta(self):
        ed = self.editor()
        valid = ed.difficulties
        seen = []
        for _ in range(len(valid) + 1):
            ed.cycle_difficulty()
            seen.append(ed.level["difficulty"])
        self.assertEqual(sorted(set(seen)), valid)
        self.assertEqual(seen[-1], seen[0])

    def test_la_musica_recorre_las_pistas_y_la_ninguna(self):
        ed = self.editor()
        ed.level.pop("music", None)
        seen = []
        for _ in range(len(TRACKS) + 1):
            ed.cycle_music()
            seen.append(ed.level.get("music"))
        self.assertEqual(seen[:-1], TRACKS)
        self.assertIsNone(seen[-1])
        self.assertNotIn("title", seen)  # la del título no es de nivel

    def test_la_habilidad_especial_se_alterna(self):
        ed = self.editor()
        was = ed.level["special_shot"]
        ed.toggle_special()
        self.assertEqual(ed.level["special_shot"], not was)
        ed.toggle_special()
        self.assertEqual(ed.level["special_shot"], was)

    def test_el_nucleo_alterna_entre_abierto_y_ciclo(self):
        ed = self.editor()
        ed.level["core_mode"] = "open"
        self.assertEqual(ed.toggle_core(), "NUCLEO CICLO")
        self.assertEqual(ed.level["core_mode"], "cycle")
        self.assertTrue(ed.dirty)
        self.assertEqual(ed.toggle_core(), "NUCLEO ABIERTO")
        self.assertEqual(ed.level["core_mode"], "open")

    def test_guardar_y_volver_a_cargar_conserva_lo_editado(self):
        ed = self.editor(2)
        self.move_to(ed, 900, 900)
        ed.place_base()
        ed.cycle_difficulty()
        ed.cycle_music()
        ed.toggle_special()
        self.move_to(ed, 100, 900)
        ed.set_start()
        expected = json.loads(json.dumps(ed.level))
        self.assertEqual(ed.save(), "GUARDADO")
        self.assertFalse(ed.dirty)
        again = LevelEditor(WORLD, TRACKS, 2)
        for key in ("bases", "difficulty", "special_shot", "player_start", "music"):
            self.assertEqual(again.level.get(key), expected.get(key), key)

    def test_un_nivel_sin_bases_no_se_guarda(self):
        ed = self.editor(2)
        ed.level["bases"] = []
        before = read(data_loader.level_path(2))
        self.assertEqual(ed.save(), "FALTAN BASES")
        self.assertEqual(read(data_loader.level_path(2)), before)

    def test_cargar_descarta_lo_editado(self):
        ed = self.editor(2)
        n = len(ed.level["bases"])
        ed.level["bases"].clear()
        ed.dirty = True
        self.assertEqual(ed.load(), "CARGADO")
        self.assertEqual(len(ed.level["bases"]), n)
        self.assertFalse(ed.dirty)

    def test_ir_a_un_nivel_que_no_existe_empieza_uno_nuevo(self):
        ed = self.editor(len(level_numbers()))
        self.assertEqual(ed.goto(1), "NIVEL NUEVO")
        self.assertEqual(ed.number, len(level_numbers()) + 1)
        self.assertEqual(ed.level["bases"], [])
        self.assertEqual(ed.level["round"], ed.number)

    def test_ir_al_siguiente_y_al_anterior_carga_de_disco(self):
        ed = self.editor(1)
        self.assertEqual(ed.goto(1), "CARGADO")
        self.assertEqual(ed.number, 2)
        ed.goto(-1)
        self.assertEqual(ed.number, 1)
        ed.goto(-1)  # no baja del primero
        self.assertEqual(ed.number, 1)

    def test_un_nivel_nuevo_guardado_entra_en_el_flujo_del_juego(self):
        last = max(level_numbers())
        ed = self.editor(last)
        ed.goto(1)
        self.move_to(ed, 200, 200)
        ed.place_base()
        self.assertEqual(ed.save(), "GUARDADO")
        self.assertIn(last + 1, level_numbers())
        state = mock.Mock(level=last)
        self.assertEqual(after_level_cleared(state, level_numbers()), "PLAY")
        self.assertEqual(state.level, last + 1)  # tras el último de antes ahora viene el nuevo

    def test_un_archivo_invalido_se_reemplaza_por_uno_nuevo_sin_romper_el_editor(self):
        with open(data_loader.level_path(2), "w", encoding="utf-8") as f:
            f.write("{ esto no es json")
        ed = self.editor(1)
        self.assertEqual(ed.goto(1), "ARCHIVO INVALIDO")
        self.assertEqual(ed.level["bases"], [])


class EditorSceneTests(TempLevels):
    def setUp(self):
        super().setUp()
        self.engine = GameEngine()

    def open(self, name):
        self.engine._apply_scene_change(name)
        return self.engine._current_scene

    def press(self, scene, action):
        scene.do_action(action, Phase.START)
        scene.do_action(action, Phase.END)

    def test_f2_entra_al_editor_desde_el_juego_y_vuelve(self):
        play = self.open("PLAY")
        play.do_action("EDITOR", Phase.START)
        self.assertEqual(self.engine._next_scene, "EDITOR")
        ed = self.open("EDITOR")
        ed.do_action("EDITOR", Phase.START)
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_esc_tambien_sale_del_editor(self):
        ed = self.open("EDITOR")
        ed.do_action("BACK", Phase.START)
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_el_editor_se_abre_en_el_nivel_que_se_jugaba(self):
        self.engine.level = 4
        ed = self.open("EDITOR")
        self.assertEqual(ed.editor.number, 4)

    def test_las_teclas_del_editor_estan_en_la_configuracion_de_entrada(self):
        keys = load_json("assets/cfg/input.json")["keyboard"]
        actions = ("EDITOR", "EDIT_SAVE", "EDIT_LOAD", "EDIT_PREV", "EDIT_NEXT", "EDIT_DIFFICULTY",
                   "EDIT_MUSIC", "EDIT_SPECIAL", "EDIT_HELP")
        for action in actions:
            self.assertIn(action, keys)
            getattr(pygame, keys[action])  # la tecla existe en pygame
        self.assertEqual(len(set(keys.values())), len(keys), "dos acciones comparten tecla")

    def test_el_editor_no_se_abre_desde_la_demo_del_modo_atractor(self):
        demo = self.open("ATTRACT")
        demo.do_action("EDITOR", Phase.START)
        self.assertIsNone(self.engine._next_scene)

    def test_poner_una_base_con_enter_y_ver_el_mensaje(self):
        ed = self.open("EDITOR")
        ed.editor.cursor = pygame.Vector2(900, 900)
        before = len(ed.editor.level["bases"])
        self.press(ed, "SELECT")
        self.assertEqual(len(ed.editor.level["bases"]), before + 1)
        self.assertEqual(ed.message, "BASE PUESTA")
        ed.do_update(3.0)
        self.assertEqual(ed.message_left, 0.0)  # el mensaje caduca

    def test_mantener_una_flecha_repite_el_movimiento(self):
        ed = self.open("EDITOR")
        x = ed.editor.cursor.x
        ed.do_action("RIGHT", Phase.START)
        self.assertEqual(ed.editor.cursor.x, x + STEP)  # el primer paso es inmediato
        ed.do_update(0.1)
        self.assertEqual(ed.editor.cursor.x, x + STEP)  # aún dentro de la espera inicial
        ed.do_update(0.5)
        self.assertGreater(ed.editor.cursor.x, x + 3 * STEP)
        ed.do_action("RIGHT", Phase.END)
        stopped = ed.editor.cursor.x
        ed.do_update(1.0)
        self.assertEqual(ed.editor.cursor.x, stopped)

    def test_las_acciones_del_editor_llegan_al_modelo(self):
        ed = self.open("EDITOR")
        before = ed.editor.level["difficulty"]
        self.press(ed, "EDIT_DIFFICULTY")
        self.assertNotEqual(ed.editor.level["difficulty"], before)
        self.press(ed, "EDIT_SPECIAL")
        self.press(ed, "EDIT_MUSIC")
        self.press(ed, "SPECIAL")  # girar las nuevas
        self.press(ed, "PAUSE")    # inicio de la nave
        self.assertTrue(ed.editor.dirty)

    def test_se_dibuja_con_y_sin_ayuda_sin_fallar(self):
        ed = self.open("EDITOR")
        screen = pygame.Surface((256, 208))
        ed.do_draw(screen)
        self.press(ed, "EDIT_HELP")
        self.assertTrue(ed.show_help)
        self.press(ed, "SELECT")
        ed.do_draw(screen)
        self.press(ed, "EDIT_HELP")
        self.assertFalse(ed.show_help)

    def test_al_salir_se_juega_el_nivel_guardado_con_los_cambios(self):
        self.engine.level = 1
        ed = self.open("EDITOR")
        n = len(ed.editor.level["bases"])
        ed.editor.cursor = pygame.Vector2(900, 900)
        self.press(ed, "SELECT")
        self.press(ed, "EDIT_SAVE")
        self.assertEqual(ed.message, "GUARDADO")
        ed.do_action("EDITOR", Phase.START)
        play = self.open("PLAY")
        bases = [t for _, t in play.world.get_component(CMinimapTrack) if t.kind == "base"]
        self.assertEqual(len(bases), n + 1)

    def test_salir_sin_guardar_no_cambia_lo_que_se_juega(self):
        self.engine.level = 1
        n = len(load_level(1)["bases"])
        ed = self.open("EDITOR")
        ed.editor.cursor = pygame.Vector2(900, 900)
        self.press(ed, "SELECT")
        ed.do_action("EDITOR", Phase.START)
        play = self.open("PLAY")
        bases = [t for _, t in play.world.get_component(CMinimapTrack) if t.kind == "base"]
        self.assertEqual(len(bases), n)

    def test_cambiar_de_nivel_en_el_editor_y_salir_juega_ese_nivel_si_existe(self):
        self.engine.level = 1
        ed = self.open("EDITOR")
        self.press(ed, "EDIT_NEXT")
        ed.do_action("EDITOR", Phase.START)
        self.assertEqual(self.engine.level, 2)

    def test_un_nivel_nuevo_sin_guardar_no_cambia_el_nivel_del_juego(self):
        last = max(level_numbers())
        self.engine.level = last
        ed = self.open("EDITOR")
        self.press(ed, "EDIT_NEXT")  # el siguiente al último no existe
        ed.do_action("EDITOR", Phase.START)
        self.assertEqual(self.engine.level, last)


if __name__ == "__main__":
    unittest.main()
