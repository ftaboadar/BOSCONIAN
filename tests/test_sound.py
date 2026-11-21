"""Pruebas de sonidos por evento y música por nivel (#33)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import create_base
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_turret import CTurret
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_base_behavior import system_turrets
from src.ecs.systems.s_base_damage import damage_base_part
from src.ecs.systems.s_explode import system_explode
from src.engine.data_loader import level_numbers, load_bases, load_json, load_level
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.menu import Menu
from src.engine.service_locator import ServiceLocator
from src.engine.sfx import play_sound

GameEngine()  # inicia pygame y los servicios para las pruebas que no son de escena
RESOURCES = load_json("assets/cfg/resources.json")
EXPLOSIONS = load_json("assets/cfg/explosions.json")
WORLD = pygame.Vector2(1024, 1024)


class Recorder:
    """Reemplaza la reproducción para anotar qué sonidos suenan."""

    def setUp(self):
        pygame.mixer.init()
        self.played = []
        self._original = ServiceLocator.sounds.play
        ServiceLocator.sounds.play = self.played.append

    def tearDown(self):
        ServiceLocator.sounds.play = self._original


class ResourcesTests(unittest.TestCase):
    def test_cada_sonido_registrado_existe(self):
        for name, path in RESOURCES["sounds"].items():
            self.assertTrue(os.path.isfile(path), f"{name}: falta {path}")

    def test_estan_los_sonidos_del_juego(self):
        for name in ("shoot", "enemy_shoot", "explosion", "player_death", "turret_hit",
                     "base_destroyed", "extra_life", "alert_yellow", "alert_red",
                     "blast_off", "menu_select"):
            self.assertIn(name, RESOURCES["sounds"])

    def test_los_sonidos_de_las_explosiones_estan_registrados(self):
        for kind, cfg in EXPLOSIONS.items():
            self.assertIn(cfg["sound"], RESOURCES["sounds"], kind)


class PlaySoundTests(Recorder, unittest.TestCase):
    def test_sonido_registrado_suena(self):
        play_sound("explosion")
        self.assertEqual(self.played, ["explosion"])

    def test_sonido_no_registrado_no_falla(self):
        play_sound("no_existe")
        self.assertEqual(self.played, [])

    def test_sin_audio_no_falla(self):
        pygame.mixer.quit()
        play_sound("explosion")
        self.assertEqual(self.played, [])


class EventSoundTests(Recorder, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.w = esper.World()

    def test_enemigo_explota_con_sonido(self):
        self.w.create_entity(CTransform(pygame.Vector2()), CExplosive("simple"), CDestroy())
        system_explode(self.w, EXPLOSIONS)
        self.assertEqual(self.played, ["explosion"])

    def test_muerte_del_jugador_suena_una_sola_vez(self):
        self.w.create_entity(CTransform(pygame.Vector2()), CExplosive("player"), CDestroy())
        system_explode(self.w, EXPLOSIONS)
        self.assertEqual(self.played, ["player_death"])

    def test_menu_suena_al_moverse_y_elegir(self):
        colors = {"normal": {"r": 255, "g": 255, "b": 255}, "selected": {"r": 255, "g": 0, "b": 0}}
        menu = Menu([{"label": "A", "action": "A"}, {"label": "B", "action": "B"}], colors, 10)
        menu.handle_action("DOWN", Phase.START)
        menu.handle_action("DOWN", Phase.END)  # soltar la tecla no suena
        menu.handle_action("SELECT", Phase.START)
        self.assertEqual(self.played, ["menu_select", "menu_select"])

    def test_torreta_dispara_con_sonido(self):
        cfg = load_bases()
        create_base(self.w, pygame.Vector2(500, 500), "vertical", cfg)
        turret, (c_t, c_tur) = next(iter(self.w.get_components(CTransform, CTurret)))
        c_tur.timer = c_tur.interval  # lista para disparar
        player = c_t.pos + self.w.component_for_entity(turret, CBasePart).offset
        system_turrets(self.w, player, WORLD, cfg, 0.0)
        self.assertIn("enemy_shoot", self.played)

    def test_destruir_torretas_y_base_suena(self):
        base = create_base(self.w, pygame.Vector2(500, 500), "vertical", load_bases())
        turrets = [e for e, c_p in self.w.get_component(CBasePart) if c_p.kind == "turret"]
        damage_base_part(self.w, turrets[0], pygame.Vector2(0, 1))
        self.assertEqual(self.played, ["turret_hit"])
        for t in turrets[1:]:
            damage_base_part(self.w, t, pygame.Vector2(0, 1))
        self.assertEqual(self.played.count("turret_hit"), 6)
        self.assertEqual(self.played[-1], "base_destroyed")
        self.assertFalse(self.w.entity_exists(base))


class SceneSoundTests(Recorder, unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()  # motor nuevo: otras pruebas pueden haber cerrado pygame
        super().setUp()
        self.music = []
        self._music_play = ServiceLocator.music.play
        ServiceLocator.music.play = lambda name, loops=-1: self.music.append(name)

    def tearDown(self):
        ServiceLocator.music.play = self._music_play
        super().tearDown()

    def open_level(self, number):
        self.engine.state.level = number
        self.engine._next_scene = None
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.blast_left = 0
        return scene

    def test_cada_nivel_pone_su_musica(self):
        for n in level_numbers():
            self.music.clear()
            self.open_level(n)
            self.assertEqual(self.music, [load_level(n)["music"]], f"nivel {n}")

    def test_el_modo_demo_va_en_silencio(self):
        self.engine._apply_scene_change("ATTRACT")
        self.assertEqual(self.music, [])

    def test_blast_off_suena_al_empezar(self):
        self.open_level(1)
        self.assertIn("blast_off", self.played)

    def test_vida_extra_suena(self):
        scene = self.open_level(1)
        state = self.engine.state
        state.score = state.next_extra_life - 5  # a 5 puntos de la vida extra
        rock = scene.world.create_entity(
            CTransform(pygame.Vector2(100, 100)), CPoints(10),
            CHitBox(pygame.Vector2(10, 10), None, "ROCK", ()))
        scene.world.create_entity(
            CTransform(pygame.Vector2(100, 100)), CVelocity(pygame.Vector2()),
            CHitBox(pygame.Vector2(2, 2), None, "PLAYER_BULLET", ("ROCK",)))
        self.played.clear()
        lives = state.lives
        scene.do_update(1 / 60)
        self.assertFalse(scene.world.entity_exists(rock))
        self.assertEqual(state.lives, lives + 1)
        self.assertIn("extra_life", self.played)


if __name__ == "__main__":
    unittest.main()
