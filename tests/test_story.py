"""Pruebas del intro animado (#35) y de la cutscene antes de jugar (#37)."""

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
from src.engine.data_loader import ConfigError, load_json, load_story
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.level_flow import after_level_cleared, after_player_died
from src.engine.scenes import story_scenes

DT = 1 / 60


def story_with(mutate):
    """story.json cargado con `mutate(cfg)` aplicado, a través de un directorio temporal."""
    cfg = copy.deepcopy(load_json("assets/cfg/story.json"))
    mutate(cfg)
    tmp = tempfile.TemporaryDirectory()
    with open(os.path.join(tmp.name, "story.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    with mock.patch.object(data_loader, "CFG_DIR", tmp.name):
        try:
            return load_story()
        finally:
            tmp.cleanup()


class StoryConfigTests(unittest.TestCase):
    def test_el_story_json_del_proyecto_es_valido(self):
        cfg = load_story()
        for name in ("intro", "cutscene"):
            self.assertTrue(cfg[name]["events"], name)
        self.assertEqual(cfg["intro"]["next"], "TITLE")
        self.assertEqual(cfg["cutscene"]["next"], "PLAY")

    def test_tipo_de_evento_desconocido_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["intro"]["events"].append({"at": 1, "type": "volar"}))

    def test_evento_fuera_de_la_duracion_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["intro"]["events"].append(
                {"at": c["intro"]["duration"] + 1, "type": "sound", "sound": "shoot"}))

    def test_falta_una_clave_del_evento_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["intro"]["events"].append({"at": 1, "type": "text", "text": "HOLA"}))

    def test_un_viaje_con_cero_segundos_falla(self):
        bad = {"at": 1, "type": "box", "size": {"w": 2, "h": 2}, "color": {"r": 1, "g": 1, "b": 1},
               "from": {"x": 0, "y": 0}, "to": {"x": 5, "y": 5}, "seconds": 0}
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["intro"]["events"].append(bad))

    def test_el_ancho_de_una_imagen_debe_ser_un_entero_positivo(self):
        for bad in (0, -5, "156", 1.5):
            with self.assertRaises(ConfigError, msg=str(bad)):
                story_with(lambda c: c["intro"]["events"][0].update(width=bad))
        self.assertEqual(story_with(lambda c: c["intro"]["events"][0].update(width=100))["intro"]["events"][0]["width"], 100)

    def test_duracion_no_positiva_falla(self):
        with self.assertRaises(ConfigError):
            story_with(lambda c: c["cutscene"].update(duration=0))


class ArrivalTests(unittest.TestCase):
    def test_la_entidad_viaja_y_se_detiene_en_su_destino(self):
        world = esper.World()
        start, target = pygame.Vector2(0, 0), pygame.Vector2(100, 40)
        ent = world.create_entity(CTransform(pygame.Vector2(start)), CSurface(pygame.Surface((1, 1))),
                                  CVelocity((target - start) / 2.0), CArrival(2.0, target))
        for _ in range(round(1.0 / DT)):
            system_movement(world, DT)
            system_arrival(world, DT)
        mid = world.component_for_entity(ent, CTransform).pos
        self.assertAlmostEqual(mid.x, 50, delta=1.5)
        for _ in range(round(1.5 / DT)):
            system_movement(world, DT)
            system_arrival(world, DT)
        self.assertEqual(tuple(world.component_for_entity(ent, CTransform).pos), (100, 40))
        self.assertEqual(tuple(world.component_for_entity(ent, CVelocity).vel), (0, 0))
        self.assertFalse(world.has_component(ent, CArrival))  # ya no se reprocesa


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

    def entities(self):
        """Entidades con superficie y posición que no son estrellas (las estrellas no tienen CSurface)."""
        return [e for e, _ in self.scene.world.get_components(CTransform, CSurface)]


class IntroSceneTests(StorySceneTestCase):
    def test_el_juego_arranca_en_el_intro_y_no_se_vuelve_a_ver_al_jugar(self):
        self.assertEqual(load_json("assets/cfg/scenes.json")["start_scene"], "INTRO")
        self.assertEqual(self.engine.cfg_scenes["start_scene"], "INTRO")

    def test_los_eventos_aparecen_en_su_momento(self):
        self.open("INTRO")
        self.assertEqual(self.entities(), [])  # nada antes del primer evento
        self.run_for(0.5)
        self.assertEqual(len(self.entities()), 1)  # el logo del título empieza a entrar
        self.run_for(3.0)  # t = 3.5 s: el logo y los tres textos
        self.assertEqual(len(self.entities()), 4)

    def test_el_logo_baja_hasta_su_sitio_y_se_queda(self):
        self.open("INTRO")
        self.run_for(0.5)
        (logo,) = self.entities()
        self.run_for(3.0)
        y = self.scene.world.component_for_entity(logo, CTransform).pos.y
        self.assertEqual(y, 56)
        self.run_for(1.0)
        self.assertEqual(self.scene.world.component_for_entity(logo, CTransform).pos.y, 56)

    def test_los_elementos_temporales_desaparecen(self):
        self.open("INTRO")
        self.run_for(6.0)  # llegan la base, los disparos y las explosiones
        busy = len(self.entities())
        self.run_for(2.5)  # la base (life) y las explosiones (animación sin repetir) ya no están
        self.assertLess(len(self.entities()), busy)

    def test_se_salta_con_cualquier_tecla_pasada_la_gracia(self):
        self.open("INTRO")
        self.scene.do_any_key()  # demasiado pronto
        self.assertIsNone(self.engine._next_scene)
        self.run_for(1.0)
        self.scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_la_tecla_de_accion_no_la_salta_pero_la_de_cualquier_tecla_si(self):
        """El motor llama a do_any_key con toda tecla, mapeada o no: ahí está el salto."""
        self.open("INTRO")
        self.run_for(1.0)
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
        self.engine._process_events()
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_termina_sola_y_va_al_titulo(self):
        self.open("INTRO")
        duration = load_story()["intro"]["duration"]
        self.run_for(duration - 0.5)
        self.assertIsNone(self.engine._next_scene)
        self.run_for(1.0)
        self.assertEqual(self.engine._next_scene, "TITLE")

    def test_se_dibuja_en_todo_momento_sin_fallar(self):
        self.open("INTRO")
        screen = pygame.Surface((256, 208))
        for _ in range(round(load_story()["intro"]["duration"] / DT)):
            self.scene.do_update(DT)
            self.scene.do_draw(screen)
            if self.engine._next_scene is not None:
                break

    def test_suena_la_musica_del_titulo_sin_reiniciarla_al_llegar_al_titulo(self):
        with mock.patch.object(story_scenes.ServiceLocator.music, "play") as play:
            self.open("INTRO")
        play.assert_called_once_with("title")

    def test_el_intro_no_modifica_la_partida(self):
        state = self.engine.state
        before = (state.score, state.lives, state.level)
        self.open("INTRO")
        self.run_for(load_story()["intro"]["duration"] + 1)
        self.assertEqual((state.score, state.lives, state.level), before)


class CutsceneTests(StorySceneTestCase):
    def texts_in_scene(self):
        return [s.surf for _, s in self.scene.world.get_component(CSurface)]

    def test_jugar_en_el_titulo_pasa_por_la_cutscene(self):
        self.open("TITLE")
        self.scene.do_action("SELECT", Phase.START)
        self.assertEqual(self.engine._next_scene, "CUTSCENE")

    def test_anuncia_la_ronda_del_nivel_elegido(self):
        for level in (1, 3):
            self.engine.level = level
            self.open("CUTSCENE")
            self.run_for(0.5)
            expected = story_scenes.load_level(level)["round"]
            font = story_scenes.ServiceLocator.fonts.get("main")
            color = pygame.Color(*(load_json("assets/cfg/menu.json")["colors"]["title"][k] for k in "rgb"))
            want = font.render(f"RONDA {expected}", False, color)
            self.assertTrue(any(s.get_size() == want.get_size() for s in self.texts_in_scene()), level)

    def test_la_nave_despega_y_sale_por_arriba(self):
        self.open("CUTSCENE")
        self.run_for(4.3)  # empieza el segundo tramo, el despegue
        ships = [(e, self.scene.world.component_for_entity(e, CTransform).pos.y)
                 for e in self.entities()
                 if self.scene.world.component_for_entity(e, CSurface).surf.get_height() == 34]
        self.assertTrue(ships)
        self.run_for(1.3)
        top = min(self.scene.world.component_for_entity(e, CTransform).pos.y for e, _ in ships
                  if self.scene.world.entity_exists(e))
        self.assertLess(top, 60)

    def test_se_salta_con_una_tecla_y_va_al_nivel(self):
        self.open("CUTSCENE")
        self.scene.do_any_key()
        self.assertIsNone(self.engine._next_scene)
        self.run_for(1.0)
        self.scene.do_any_key()
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_termina_sola_y_va_al_nivel(self):
        self.open("CUTSCENE")
        self.run_for(load_story()["cutscene"]["duration"] + 0.5)
        self.assertEqual(self.engine._next_scene, "PLAY")

    def test_la_cutscene_conserva_el_nivel_y_no_toca_la_partida(self):
        self.engine.level = 4
        self.engine.start_game()
        before = (self.engine.state.level, self.engine.state.lives, self.engine.state.score)
        self.open("CUTSCENE")
        self.run_for(load_story()["cutscene"]["duration"] + 0.5)
        self.assertEqual(self.engine._next_scene, "PLAY")
        self.assertEqual((self.engine.state.level, self.engine.state.lives, self.engine.state.score), before)

    def test_continuar_o_pasar_de_nivel_no_repite_la_cutscene(self):
        """Solo el 'Jugar' del título la lleva: las demás rutas al nivel van directo a PLAY."""
        self.assertEqual(after_player_died(self.engine.state), "PLAY")
        self.assertEqual(after_level_cleared(self.engine.state, [1, 2, 3]), "PLAY")

    def test_se_dibuja_sin_fallar(self):
        self.open("CUTSCENE")
        screen = pygame.Surface((256, 208))
        for _ in range(round(load_story()["cutscene"]["duration"] / DT)):
            self.scene.do_update(DT)
            self.scene.do_draw(screen)
            if self.engine._next_scene is not None:
                break


if __name__ == "__main__":
    unittest.main()
