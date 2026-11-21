"""Pruebas del sistema de alertas VERDE, AMARILLA y ROJA (#26)."""

import os
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import create_alert, create_base, create_enemy, create_enemy_spawner
from src.ecs.components.c_alert import AlertLevel, CAlert
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_alert import alert_base_destroyed, system_alert
from src.ecs.systems.s_base_behavior import system_base_cores
from src.ecs.systems.s_enemy_spawner import system_enemy_spawner
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_invulnerable import CInvulnerable
from src.ecs.systems.s_base_damage import damage_base_part
from src.engine.data_loader import level_numbers, load_bases, load_enemies, load_level
from src.engine.difficulty import difficulty_params
from src.engine.game_engine import GameEngine
from src.engine.service_locator import ServiceLocator

GameEngine()  # inicia pygame y los servicios
DT = 1 / 60
PARAMS = {"yellow_after": 5, "red_after": 60, "calm_seconds": 4,
          "red_speed_factor": 2.0, "red_spawn_factor": 2.0}


class Recorder:
    """Reemplaza la reproducción para anotar qué sonidos suenan."""

    def setUp(self):
        pygame.mixer.init()
        self.played = []
        self._original = ServiceLocator.sounds.play
        ServiceLocator.sounds.play = self.played.append

    def tearDown(self):
        ServiceLocator.sounds.play = self._original


class AlertTests(Recorder, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.world = esper.World()
        self.alert = self.world.component_for_entity(create_alert(self.world, PARAMS), CAlert)

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            system_alert(self.world, DT)

    def test_empieza_en_verde_y_pasa_a_amarilla_tras_poco_tiempo(self):
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.run_for(4.9)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.assertEqual(self.played, [])
        self.run_for(0.2)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)
        self.assertEqual(self.played, ["alert_yellow"])

    def test_destruir_una_base_vuelve_a_verde_un_rato_y_luego_a_amarilla(self):
        self.run_for(10)
        self.played.clear()
        alert_base_destroyed(self.world)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.assertEqual(self.played, ["alert_green"])
        self.run_for(3.9)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.run_for(0.2)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)
        self.assertEqual(self.played, ["alert_green", "alert_yellow"])

    def test_pasa_a_roja_por_tiempo_y_suena_una_sola_vez(self):
        self.run_for(59.9)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)
        self.run_for(5)
        self.assertEqual(self.alert.level, AlertLevel.RED)
        self.assertEqual(self.played, ["alert_yellow", "alert_red"])

    def test_la_calma_tras_una_base_no_retrasa_la_roja(self):
        self.run_for(58)
        alert_base_destroyed(self.world)  # verde hasta el segundo 62
        self.run_for(2.1)
        self.assertEqual(self.alert.level, AlertLevel.RED)

    def test_de_roja_no_se_baja_ni_destruyendo_una_base(self):
        self.run_for(61)
        self.played.clear()
        alert_base_destroyed(self.world)
        self.run_for(30)
        self.assertEqual(self.alert.level, AlertLevel.RED)
        self.assertEqual(self.played, [])

    def test_una_base_destruida_al_empezar_no_acorta_el_verde_inicial(self):
        self.run_for(0.5)
        alert_base_destroyed(self.world)  # la calma (4 s) es menos de lo que quedaba (4.5 s)
        self.run_for(4.3)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.run_for(0.3)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)

    def test_una_base_destruida_en_el_verde_inicial_no_suena_pero_alarga_la_calma(self):
        self.run_for(4)
        alert_base_destroyed(self.world)
        self.assertEqual(self.played, [])
        self.run_for(3.9)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.run_for(0.2)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)


WORLD = pygame.Vector2(1024, 1024)
PLAYER = pygame.Vector2(500, 500)
PLAYER_SPEED = 80


class AlertEnemyTests(Recorder, unittest.TestCase):
    """Lo que la alerta cambia en los enemigos: cuántos salen y a qué velocidad."""

    def setUp(self):
        super().setUp()
        self.world = esper.World()
        self.rng = random.Random(3)
        self.cfg = load_enemies()
        self.cfg["spawn"].update(interval_seconds={"easy": 1.0, "hard": 1.0},
                                 max_alive={"easy": 100, "hard": 100})
        self.alert = self.world.component_for_entity(create_alert(self.world, PARAMS), CAlert)
        create_enemy_spawner(self.world, self.cfg, 0.0)

    def run_for(self, seconds, alert=True):
        for _ in range(round(seconds / DT)):
            if alert:
                system_alert(self.world, DT)
            system_enemy_spawner(self.world, PLAYER, WORLD, self.cfg, PLAYER_SPEED, DT, self.rng)

    def speeds(self):
        return [c_v.vel.length() for _, (c_v, _c_s)
                in self.world.get_components(CVelocity, CEnemyState)]

    def test_en_verde_no_salen_enemigos_y_en_amarilla_si(self):
        self.run_for(4.9)
        self.assertEqual(self.speeds(), [])
        self.run_for(5.2)  # amarilla desde el segundo 5: uno por segundo
        self.assertEqual(len(self.speeds()), 5)

    def test_tras_destruir_una_base_dejan_de_salir_mientras_dura_el_verde(self):
        self.run_for(10.1)
        before = len(self.speeds())
        alert_base_destroyed(self.world)
        self.run_for(3.9)
        self.assertEqual(len(self.speeds()), before)
        self.run_for(3.0)
        self.assertGreater(len(self.speeds()), before)

    def test_en_roja_salen_al_doble_de_ritmo_y_al_doble_de_velocidad(self):
        self.alert.level = AlertLevel.YELLOW
        self.run_for(10.1, alert=False)
        yellow = self.speeds()
        self.world.clear_database()
        self.alert = self.world.component_for_entity(create_alert(self.world, PARAMS), CAlert)
        self.alert.level = AlertLevel.RED
        create_enemy_spawner(self.world, self.cfg, 0.0)
        self.run_for(10.1, alert=False)
        red = self.speeds()
        self.assertEqual((len(yellow), len(red)), (10, 20))
        for kind_speed in set(round(s, 3) for s in red):
            self.assertIn(round(kind_speed / 2, 3), set(round(s, 3) for s in yellow))

    def test_en_roja_el_tope_de_enemigos_vivos_tambien_se_dobla(self):
        self.cfg["spawn"]["max_alive"] = {"easy": 3, "hard": 3}
        counts = []
        for level in (AlertLevel.YELLOW, AlertLevel.RED):
            self.world.clear_database()
            alert = self.world.component_for_entity(create_alert(self.world, PARAMS), CAlert)
            alert.level = level
            create_enemy_spawner(self.world, self.cfg, 0.0)
            self.run_for(20, alert=False)
            counts.append(len(self.speeds()))
        self.assertEqual(counts, [3, 6])

    def test_al_pasar_a_roja_los_enemigos_que_ya_estaban_doblan_su_velocidad(self):
        enemy = create_enemy(self.world, "I", pygame.Vector2(100, 100), pygame.Vector2(1, 0),
                             self.cfg, PLAYER_SPEED, 0.0, self.rng)
        vel = self.world.component_for_entity(enemy, CVelocity)
        before = vel.vel.length()
        self.alert.elapsed = PARAMS["red_after"] - 0.001
        system_alert(self.world, DT)
        system_alert(self.world, DT)
        self.assertEqual(self.alert.level, AlertLevel.RED)
        self.assertAlmostEqual(vel.vel.length(), before * 2)

    def core_launches(self, level, seconds=12.0):
        """Enemigos que lanza en `seconds` el núcleo con ciclo de una base, con esa alerta."""
        self.world.clear_database()
        self.alert = self.world.component_for_entity(create_alert(self.world, PARAMS), CAlert)
        self.alert.level = level
        create_base(self.world, pygame.Vector2(300, 300), "vertical", load_bases(), "cycle", 1.0,
                    self.rng)
        for _ in range(round(seconds / DT)):
            system_base_cores(self.world, PLAYER, WORLD, self.cfg, PLAYER_SPEED, DT)
        return self.speeds()

    def test_los_nucleos_no_lanzan_enemigos_en_verde_y_en_roja_salen_mas_rapidos(self):
        self.assertEqual(self.core_launches(AlertLevel.GREEN), [])
        yellow = self.core_launches(AlertLevel.YELLOW)
        red = self.core_launches(AlertLevel.RED)
        self.assertGreater(len(yellow), 0)
        self.assertAlmostEqual(red[0], yellow[0] * 2)


class AlertConfigTests(unittest.TestCase):
    def test_cada_nivel_pasa_pronto_a_amarilla_y_mucho_despues_a_roja(self):
        for n in level_numbers():
            params = difficulty_params(load_level(n))
            self.assertTrue(0 < params["yellow_after"] <= 10, f"nivel {n}")
            self.assertGreater(params["red_after"], params["yellow_after"] * 5, f"nivel {n}")
            self.assertGreater(params["calm_seconds"], 0)
            self.assertAlmostEqual(params["red_speed_factor"], 2, delta=0.5)
            self.assertAlmostEqual(params["red_spawn_factor"], 2, delta=0.5)


class PlaySceneAlertTests(Recorder, unittest.TestCase):
    def setUp(self):
        random.seed(1)  # obstáculos al azar: semilla fija
        self.engine = GameEngine()
        super().setUp()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.world = self.scene.world
        self.world.add_component(self.scene.player, CInvulnerable())  # que no muera en la prueba
        self.alert = self.world.get_component(CAlert)[0][1]
        self.params = self.scene.difficulty

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.do_update(DT)

    def test_el_nivel_empieza_en_verde_y_la_cuenta_no_corre_en_blast_off_ni_en_pausa(self):
        from src.engine.input.command import Phase
        self.run_for(self.engine.cfg_world["blast_off"]["seconds"] + 0.1)
        self.scene.do_action("PAUSE", Phase.START)
        self.run_for(self.params["yellow_after"] + 1)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.scene.do_action("PAUSE", Phase.START)
        self.run_for(self.params["yellow_after"] - 0.5)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.assertEqual(len(self.world.get_component(CEnemyState)), 0)
        self.run_for(0.6)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)
        self.assertIn("alert_yellow", self.played)

    def test_destruir_una_base_en_el_nivel_vuelve_a_verde(self):
        self.scene.blast_left = 0
        self.run_for(self.params["yellow_after"] + 0.1)
        self.assertEqual(self.alert.level, AlertLevel.YELLOW)
        base = self.world.get_component(CBase)[0][0]
        for part, c_p in self.world.get_component(CBasePart):
            if c_p.base == base and c_p.kind == "turret":
                damage_base_part(self.world, part, pygame.Vector2(0, 1))
        self.scene.do_update(DT)
        self.assertEqual(self.alert.level, AlertLevel.GREEN)
        self.assertIn("alert_green", self.played)

    def test_el_panel_muestra_la_alerta_con_su_color(self):
        self.scene.blast_left = 0
        seen = []
        for level in AlertLevel:
            self.alert.level = level
            screen = pygame.Surface((256, 208))
            self.scene.do_draw(screen)
            panel = screen.subsurface(pygame.Rect(176, 163, 80, 8))
            colors = {tuple(panel.get_at((x, y)))[:3] for x in range(80) for y in range(8)}
            seen.append(colors - {(0, 0, 0)})
        self.assertEqual(seen, [{(0, 255, 0)}, {(255, 220, 0)}, {(255, 60, 60)}])


if __name__ == "__main__":
    unittest.main()
