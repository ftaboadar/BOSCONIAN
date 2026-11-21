"""Pruebas de la secuencia de arranque, copiada del Bosconian original (#35, #37):
pantalla inicial con la barra en ceros, logo sobre el verde, créditos, título con «PUSH BUTTON TO
START», menú y la cinemática de «LEVEL n» antes de jugar."""

import copy
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.ecs.components.c_arrival import CArrival
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_arrival import system_arrival
from src.ecs.systems.s_movement import system_movement
from src.engine import data_loader
from src.engine.data_loader import ConfigError, level_numbers, load_json, load_level, load_story
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.level_flow import after_level_cleared, after_player_died
from src.engine.scenes import story_scenes
from src.engine.timeline import Timeline

DT = 1 / 60
STORY = load_json("assets/cfg/story.json")
SECTIONS = ("splash", "logo_slide", "byline", "title", "cutscene")


def rgb(color: dict) -> tuple:
    return (color["r"], color["g"], color["b"])


def story_with(mutate):
    """story.json cargado con `mutate(cfg)` aplicado, a través de un directorio temporal."""
    cfg = copy.deepcopy(load_json("assets/cfg/story.json"))
    mutate(cfg)
    tmp = tempfile.TemporaryDirectory()
    with open(os.path.join(tmp.name, "story.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    with open(os.path.join(tmp.name, "menu.json"), "w", encoding="utf-8") as f:
        json.dump(load_json("assets/cfg/menu.json"), f)
    with mock.patch.object(data_loader, "CFG_DIR", tmp.name):
        try:
            return load_story()
        finally:
            tmp.cleanup()


class StoryConfigTests(unittest.TestCase):
    def test_el_story_json_del_proyecto_es_valido(self):
        cfg = load_story()
        for name in SECTIONS:
            self.assertTrue(cfg[name]["events"], name)
        self.assertEqual([cfg[n]["next"] for n in ("splash", "logo_slide", "byline", "cutscene")],
                         ["LOGO_SLIDE", "BYLINE", "TITLE", "PLAY"])

    def test_tipo_de_evento_desconocido_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["splash"]["events"].append({"at": 1, "type": "volar"}))

    def test_evento_fuera_de_la_duracion_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["splash"]["events"].append(
                {"at": c["splash"]["duration"] + 1, "type": "sound", "sound": "shoot"}))

    def test_falta_una_clave_del_evento_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["splash"]["events"].append({"at": 1, "type": "text"}))

    def test_un_texto_quieto_necesita_posicion(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["splash"]["events"].append({"at": 1, "type": "text", "text": "HOLA"}))

    def test_un_viaje_con_cero_segundos_falla(self):
        bad = {"at": 1, "type": "box", "size": {"w": 2, "h": 2}, "color": {"r": 1, "g": 1, "b": 1},
               "from": {"x": 0, "y": 0}, "to": {"x": 5, "y": 5}, "seconds": 0}
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["splash"]["events"].append(bad))

    def test_un_color_de_texto_desconocido_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["splash"]["events"][0].update(color="fucsia"))

    def test_el_ancho_de_una_imagen_debe_ser_un_entero_positivo(self):
        for bad in (0, -5, "168", 1.5):
            with self.assertRaises(ConfigError, msg=str(bad)):
                story_with(lambda c: c["logo_slide"]["events"][0].update(width=bad))
        self.assertEqual(story_with(lambda c: c["logo_slide"]["events"][0].update(width=100))
                         ["logo_slide"]["events"][0]["width"], 100)

    def test_duracion_no_positiva_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["cutscene"].update(duration=0))

    def test_cada_seccion_necesita_sus_eventos(self):
        for name in SECTIONS:
            with self.assertRaises(ConfigError, msg=name):
                story_with(lambda c: c[name].pop("events"))

    def test_el_titulo_no_necesita_duracion_ni_siguiente(self):
        for key in ("next", "duration", "stars_speed"):
            self.assertNotIn(key, STORY["title"])
        load_story()


class ArrivalTests(unittest.TestCase):
    def test_la_entidad_viaja_y_se_detiene_en_su_destino(self):
        world = esper.World()
        start, target = pygame.Vector2(0, 0), pygame.Vector2(100, 40)
        ent = world.create_entity(CTransform(pygame.Vector2(start)), CSurface(pygame.Surface((1, 1))),
                                  CVelocity((target - start) / 2.0), CArrival(2.0, target))
        for _ in range(round(1.0 / DT)):
            system_movement(world, DT)
            system_arrival(world, DT)
        self.assertAlmostEqual(world.component_for_entity(ent, CTransform).pos.x, 50, delta=1.5)
        for _ in range(round(1.5 / DT)):
            system_movement(world, DT)
            system_arrival(world, DT)
        self.assertEqual(tuple(world.component_for_entity(ent, CTransform).pos), (100, 40))
        self.assertEqual(tuple(world.component_for_entity(ent, CVelocity).vel), (0, 0))
        self.assertFalse(world.has_component(ent, CArrival))


class TimelineTests(unittest.TestCase):
    def setUp(self):
        GameEngine()
        self.world = esper.World()
        self.colors = load_json("assets/cfg/menu.json")["colors"]

    def text(self, at, group=None, **extra):
        event = {"at": at, "type": "text", "text": "HOLA", "color": "normal", "pos": {"x": 10, "y": 10}}
        if group:
            event["group"] = group
        event.update(extra)
        return event

    def test_los_eventos_aparecen_en_su_momento_y_en_orden(self):
        tl = Timeline(self.world, [self.text(1.0), self.text(0.5)], self.colors)
        tl.update(0.4)
        self.assertEqual(len(self.world.get_component(CSurface)), 0)
        tl.update(0.2)
        self.assertEqual(len(self.world.get_component(CSurface)), 1)
        tl.update(0.6)
        self.assertEqual(len(self.world.get_component(CSurface)), 2)

    def test_un_grupo_se_quita_junto_y_lo_que_no_habia_aparecido_ya_no_aparece(self):
        tl = Timeline(self.world, [self.text(0.0, "push"), self.text(0.0), self.text(5.0, "push")], self.colors)
        tl.update(0.1)
        self.assertEqual(len(self.world.get_component(CSurface)), 2)
        tl.remove_group("push")
        self.assertEqual(len(self.world.get_component(CSurface)), 1)
        tl.update(6.0)
        self.assertEqual(len(self.world.get_component(CSurface)), 1)  # el del grupo pendiente no salió

    def test_un_texto_puede_viajar_y_detenerse(self):
        tl = Timeline(self.world, [{"at": 0, "type": "text", "text": "HOLA", "color": "normal",
                                    "from": {"x": -100, "y": 50}, "to": {"x": 96, "y": 50}, "seconds": 1.0}], self.colors)
        for _ in range(round(1.5 / DT)):
            tl.update(DT)
        (pos,) = [t.pos for _, t in self.world.get_component(CTransform)]
        self.assertEqual((pos.x, pos.y), (96, 50))

    def test_los_campos_se_reemplazan_en_los_textos(self):
        tl = Timeline(self.world, [self.text(0.0, text="NIVEL {level}")], self.colors, {"level": 7})
        tl.update(0.1)
        width = [s.surf.get_width() for _, s in self.world.get_component(CSurface)][0]
        self.assertEqual(width, len("NIVEL 7") * 8)


class StorySceneTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()

    def open(self, name):
        self.engine._apply_scene_change(name)
        self.scene = self.engine._current_scene
        return self.scene

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.do_update(DT)
            if self.engine._next_scene is not None:
                return

    def draw(self):
        self.engine._draw()
        return self.engine.screen


class SplashTests(StorySceneTestCase):
    def test_el_juego_arranca_en_la_pantalla_inicial(self):
        self.assertEqual(load_json("assets/cfg/scenes.json")["start_scene"], "SPLASH")
        self.assertEqual(self.engine.cfg_scenes["start_scene"], "SPLASH")

    def test_la_musica_empieza_antes_de_cargar_nada(self):
        with mock.patch.object(story_scenes.ServiceLocator.music, "play") as play:
            self.open("SPLASH")
        play.assert_called_once_with("title")

    def test_la_barra_aparece_en_ceros_y_sin_vidas(self):
        self.engine.state.hi_score, self.engine.state.score = 20000, 7650
        scene = self.open("SPLASH")
        state = scene.panel_state()
        self.assertEqual((state.hi_score, state.score), (0, 0))
        self.assertFalse(scene.panel_lives)
        screen = self.draw()
        panel = self.engine.hud.panel
        self.assertEqual(tuple(screen.get_at((panel.left + 1, 61)))[:3], (128, 255, 160))  # CONDITION ya en verde

    def test_el_texto_del_centro_es_rojo_la_marca_y_blanco_el_resto(self):
        scene = self.open("SPLASH")
        self.run_for(0.2)
        self.draw()
        texts = [e for e in STORY["splash"]["events"] if e["type"] == "text"]
        self.assertEqual(texts[0]["color"], "brand")
        self.assertEqual({t["color"] for t in texts[1:]}, {"normal"})
        self.assertEqual(len(self.scene.world.get_component(CSurface)), len(texts))

    def test_pasa_sola_al_verde_con_el_logo_y_se_salta_directo_al_titulo(self):
        self.open("SPLASH")
        self.run_for(STORY["splash"]["duration"] + 0.5)
        self.assertEqual(self.engine._next_scene, "LOGO_SLIDE")
        self.engine._next_scene = None
        scene = self.open("SPLASH")
        self.run_for(1.0)
        scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_no_se_puede_saltar_en_el_primer_instante(self):
        scene = self.open("SPLASH")
        scene.do_any_key()
        self.assertIsNone(self.engine._next_scene)


class LogoSlideTests(StorySceneTestCase):
    def test_el_fondo_es_verde_menta_y_sin_estrellas(self):
        scene = self.open("LOGO_SLIDE")
        self.assertFalse(scene.stars)
        self.run_for(0.1)
        screen = self.draw()
        mint = rgb(STORY["logo_slide"]["background"])
        self.assertEqual(tuple(screen.get_at((5, 5)))[:3], mint)
        self.assertEqual(tuple(screen.get_at((5, 200)))[:3], mint)

    def test_el_logo_entra_por_la_derecha_hasta_el_centro(self):
        scene = self.open("LOGO_SLIDE")
        self.run_for(0.5)
        (logo_t,) = [t for _, (t, s) in scene.world.get_components(CTransform, CSurface)]
        self.assertGreater(logo_t.pos.x, self.engine.viewport.centerx)       # aún a la derecha
        self.run_for(2.0)
        self.assertEqual(logo_t.pos.x, self.engine.viewport.centerx)         # y se queda al centro
        self.assertEqual(logo_t.pos.y, 84)

    def test_la_barra_ya_muestra_los_valores_reales(self):
        self.engine.state.hi_score = 20000
        scene = self.open("LOGO_SLIDE")
        self.assertEqual(scene.panel_state().hi_score, 20000)

    def test_el_logo_no_trae_la_mancha_gris_translucida(self):
        from src.create.prefab_creator import logo_surface
        surf = logo_surface(168)
        translucent_white = [(x, y) for x in range(surf.get_width()) for y in range(surf.get_height())
                             if 0 < surf.get_at((x, y)).a < 100 and min(surf.get_at((x, y))[:3]) > 240]
        self.assertEqual(translucent_white, [])
        self.assertEqual(surf.get_width(), 168)

    def test_sigue_a_los_creditos(self):
        self.open("LOGO_SLIDE")
        self.run_for(STORY["logo_slide"]["duration"] + 0.2)
        self.assertEqual(self.engine._next_scene, "BYLINE")


class BylineTests(StorySceneTestCase):
    def test_muestra_el_logo_y_los_usuarios_de_github_del_equipo(self):
        texts = [e["text"] for e in STORY["byline"]["events"] if e["type"] == "text"]
        self.assertIn("ARRANGED BY", texts)
        team = ["FTABOADAR", "JDBU2002", "JZARRUKE", "SANTI8194"]
        for name in team:
            self.assertIn(name, texts)
        self.assertEqual(texts[texts.index("ARRANGED BY") + 1:], team)  # en ese orden, tras «ARRANGED BY»
        self.assertTrue(any("©" in t for t in texts))

    def test_es_negra_con_estrellas_y_el_logo_al_centro(self):
        scene = self.open("BYLINE")
        self.assertTrue(scene.stars)
        self.run_for(0.2)
        screen = self.draw()
        self.assertNotEqual(tuple(screen.get_at((3, 3)))[:3], (126, 196, 152))
        logos = [t.pos for _, (t, s) in scene.world.get_components(CTransform, CSurface) if s.surf.get_width() == 168]
        self.assertEqual([(p.x, p.y) for p in logos], [(96, 84)])

    def test_los_nombres_caben_en_el_campo(self):
        for e in STORY["byline"]["events"]:
            if e["type"] == "text":
                self.assertLessEqual(len(e["text"]) * 8, self.engine.viewport.w, e["text"])

    def test_sigue_al_titulo(self):
        self.open("BYLINE")
        self.run_for(STORY["byline"]["duration"] + 0.2)
        self.assertEqual(self.engine._next_scene, "TITLE")


class FullSequenceTests(unittest.TestCase):
    def test_el_orden_completo_con_la_persiana_entre_pantallas(self):
        engine = GameEngine()
        engine.delta_time = DT
        engine._apply_scene_change(engine.cfg_scenes["start_scene"])
        seen = [type(engine._current_scene).__name__]
        for _ in range(60 * 40):
            engine._frame()
            name = type(engine._current_scene).__name__
            if name != seen[-1]:
                seen.append(name)
            if name == "TitleScene" and not engine.shutter.busy:
                break
        self.assertEqual(seen, ["SplashScene", "LogoSlideScene", "BylineScene", "TitleScene"])

    def test_pulsar_una_tecla_salta_todo_hasta_el_titulo(self):
        engine = GameEngine()
        engine.delta_time = DT
        engine._apply_scene_change("SPLASH")
        for _ in range(30):
            engine._frame()
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        for _ in range(60):
            engine._frame()
        self.assertEqual(type(engine._current_scene).__name__, "TitleScene")


class TitleTests(StorySceneTestCase):
    def test_fondo_verde_logo_subtitulo_y_push_button(self):
        scene = self.open("TITLE")
        self.run_for(2.0)
        screen = self.draw()
        mint = rgb(STORY["title"]["background"])
        self.assertEqual(tuple(screen.get_at((4, 4)))[:3], mint)
        texts = [e["text"] for e in STORY["title"]["events"] if e["type"] == "text"]
        self.assertIn("PUSH BUTTON TO START", texts)
        self.assertEqual(scene.mode, "push")

    def test_push_button_entra_por_la_izquierda_y_despues_parpadea(self):
        scene = self.open("TITLE")
        self.run_for(0.4)
        (push,) = scene.timeline.groups["push"]
        self.assertLess(scene.world.component_for_entity(push, CTransform).pos.x, self.engine.viewport.centerx)
        self.run_for(3.0)
        states = set()
        for _ in range(round(2.0 / DT)):
            scene.do_update(DT)
            states.add(scene.world.component_for_entity(push, CSurface).surf.get_width() > 1)
        self.assertEqual(states, {True, False})  # visible y apagado

    def test_un_boton_abre_el_menu_sin_elegir_nada(self):
        scene = self.open("TITLE")
        self.run_for(1.0)
        scene.do_any_key()          # la tecla llega como «cualquier tecla»...
        scene.do_action("SELECT", Phase.START)   # ...y también como la acción mapeada
        self.assertEqual(scene.mode, "menu")
        self.assertIsNone(self.engine._next_scene)   # la misma pulsación no eligió «JUGAR»
        self.assertIsNone(scene.timeline.groups.get("push"))

    def test_ya_con_el_menu_abierto_enter_elige(self):
        scene = self.open("TITLE")
        self.run_for(1.0)
        scene.do_any_key()
        scene.do_update(DT)
        scene.do_action("SELECT", Phase.START)
        self.assertEqual(self.engine._next_scene, "CUTSCENE")

    def test_el_menu_aparece_sobre_el_mismo_fondo_verde(self):
        scene = self.open("TITLE")
        self.run_for(2.5)
        scene.do_any_key()
        scene.do_update(DT)
        screen = self.draw()
        mint = rgb(STORY["title"]["background"])
        self.assertEqual(tuple(screen.get_at((4, 4)))[:3], mint)
        top = STORY["title"]["menu_top"]
        yellow = [(x, y) for x in range(192) for y in range(top - 6, top + 6)
                  if tuple(screen.get_at((x, y)))[:3] == (255, 220, 0)]
        self.assertTrue(yellow)  # la opción elegida, en amarillo

    def test_el_menu_no_se_pisa_con_los_textos_de_abajo(self):
        last_menu_line = STORY["title"]["menu_top"] + 3 * 14 + 4
        bottom = min(e["pos"]["y"] for e in STORY["title"]["events"]
                     if e["type"] == "text" and e["text"] in ("UNIANDES", "MISO")) - 4
        self.assertLess(last_menu_line, bottom)

    def test_no_se_abre_en_el_primer_instante(self):
        scene = self.open("TITLE")
        scene.do_any_key()
        self.assertEqual(scene.mode, "push")

    def test_sin_tocar_nada_arranca_el_modo_atractor(self):
        scene = self.open("TITLE")
        self.run_for(self.engine.cfg_menu["attract"]["idle_seconds"] + 0.5)
        self.assertEqual(self.engine._next_scene, "ATTRACT")

    def test_la_barra_del_titulo_muestra_los_valores_reales_y_sin_vidas(self):
        self.engine.state.hi_score = 20000
        scene = self.open("TITLE")
        self.assertEqual(scene.panel_state().hi_score, 20000)
        self.assertFalse(scene.panel_lives)

    def test_la_musica_del_titulo_sigue_sin_reiniciarse(self):
        with mock.patch.object(story_scenes.ServiceLocator.music, "play") as play:
            self.open("TITLE")
        play.assert_called_once_with("title")


class CutsceneTests(StorySceneTestCase):
    def texts(self):
        return [s.surf for _, s in self.scene.world.get_component(CSurface)]

    def test_jugar_en_el_titulo_va_a_la_cinematica_y_esta_al_nivel(self):
        scene = self.open("TITLE")
        self.run_for(1.0)
        scene.do_any_key()
        scene.do_update(DT)
        scene.do_action("SELECT", Phase.START)
        self.assertEqual(self.engine._next_scene, "CUTSCENE")

    def test_muestra_el_numero_de_nivel_y_su_nombre_en_azul(self):
        for number in (1, 4, 10):
            self.engine.level = number
            self.open("CUTSCENE")
            self.run_for(0.2)
            font = story_scenes.ServiceLocator.fonts.get("main")
            for text in (f"LEVEL {number}", load_level(number)["subtitle"]):
                want = font.render(text, False, (64, 128, 255))
                self.assertTrue(any(s.get_size() == want.get_size() for s in self.texts()), (number, text))

    def test_el_nivel_1_se_llama_como_en_el_original(self):
        self.assertEqual(load_level(1)["subtitle"], "AROUND THE PLANET RED.")

    def test_todos_los_niveles_tienen_nombre_que_cabe_en_el_campo(self):
        names = []
        for n in level_numbers():
            subtitle = load_level(n)["subtitle"]
            self.assertLessEqual(len(subtitle), 24, subtitle)
            self.assertEqual(subtitle, subtitle.upper())
            names.append(subtitle)
        self.assertEqual(len(set(names)), len(names), "dos niveles se llaman igual")

    def test_dibuja_la_nave_grande_y_las_dos_laterales(self):
        self.open("CUTSCENE")
        self.run_for(0.2)
        heights = sorted(s.get_height() for s in self.texts() if s.get_height() > 20)
        self.assertEqual(len(heights), 3)
        self.assertGreater(heights[-1], heights[0])  # la del centro es la más grande

    def test_las_vidas_se_ven_en_la_cinematica_con_los_valores_reales(self):
        scene = self.open("CUTSCENE")
        self.assertTrue(scene.panel_lives)
        self.assertIs(scene.panel_state(), self.engine.state)

    def test_se_salta_con_una_tecla_y_va_al_nivel(self):
        scene = self.open("CUTSCENE")
        scene.do_any_key()
        self.assertIsNone(self.engine._next_scene)  # demasiado pronto
        self.run_for(1.0)
        scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_termina_sola_y_va_al_nivel(self):
        self.open("CUTSCENE")
        self.run_for(STORY["cutscene"]["duration"] + 0.5)
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_no_toca_la_partida(self):
        self.engine.level = 4
        self.engine.start_game()
        before = (self.engine.state.level, self.engine.state.lives, self.engine.state.score)
        self.open("CUTSCENE")
        self.run_for(STORY["cutscene"]["duration"] + 0.5)
        self.assertEqual((self.engine.state.level, self.engine.state.lives, self.engine.state.score), before)

    def test_continuar_o_pasar_de_nivel_no_repite_ni_la_persiana_ni_la_cinematica(self):
        self.assertEqual(after_player_died(self.engine.state), "PLAY")
        self.assertEqual(after_level_cleared(self.engine.state, [1, 2, 3]), "PLAY")
        self.assertFalse(self.engine.shutter.wants("PLAY"))
        self.assertFalse(self.engine.shutter.wants("CUTSCENE"))  # el verde ya no es la entrada al juego

    def test_se_dibuja_sin_fallar_durante_toda_la_cinematica(self):
        self.open("CUTSCENE")
        for _ in range(round(STORY["cutscene"]["duration"] / DT)):
            self.scene.do_update(DT)
            self.draw()
            if self.engine._next_scene is not None:
                break


class LevelSubtitleConfigTests(unittest.TestCase):
    def load_with(self, **changes):
        level = {**load_json("assets/cfg/levels/level_01.json"), **changes}
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "level_01.json"), "w", encoding="utf-8") as f:
                json.dump(level, f)
            with mock.patch.object(data_loader, "LEVELS_DIR", d):
                return load_level(1)

    def test_el_nombre_del_nivel_es_opcional(self):
        level = load_json("assets/cfg/levels/level_01.json")
        level.pop("subtitle")
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "level_01.json"), "w", encoding="utf-8") as f:
                json.dump(level, f)
            with mock.patch.object(data_loader, "LEVELS_DIR", d):
                self.assertNotIn("subtitle", load_level(1))

    def test_un_nombre_demasiado_largo_o_que_no_es_texto_falla(self):
        for bad in ("X" * 25, 5, ["A"]):
            with self.assertRaises(ConfigError, msg=str(bad)):
                self.load_with(subtitle=bad)
        self.assertEqual(self.load_with(subtitle="X" * 24)["subtitle"], "X" * 24)

    def test_el_editor_conserva_el_nombre_al_guardar(self):
        text = data_loader.format_level(load_json("assets/cfg/levels/level_01.json"))
        self.assertIn('"subtitle": "AROUND THE PLANET RED."', text)
        self.assertLess(text.index('"subtitle"'), text.index('"difficulty"'))  # tras la ronda, como en los archivos


if __name__ == "__main__":
    unittest.main()
