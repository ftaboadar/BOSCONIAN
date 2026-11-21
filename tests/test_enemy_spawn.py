"""Pruebas de los enemigos I, P y E (#21): puntos por tipo y spawn alrededor del jugador."""

import copy
import json
import os
import random
import sys
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import create_enemy, create_enemy_spawner
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_enemy_spawner import system_enemy_despawn, system_enemy_spawner
from src.engine.camera import wrap_delta
from src.engine import data_loader
from src.engine.data_loader import ConfigError, load_enemies
from src.engine.game_engine import GameEngine

WORLD = pygame.Vector2(1024, 1024)
PLAYER_SPEED = 80
DT = 1 / 60


class EnemyPointsTests(unittest.TestCase):
    def test_cada_tipo_vale_sus_puntos_con_la_config_real(self):
        world = esper.World()
        cfg = load_enemies()
        points = {}
        for kind in ("I", "P", "E"):
            e = create_enemy(world, kind, pygame.Vector2(500, 500), pygame.Vector2(0, -1),
                             cfg, PLAYER_SPEED, 0.5, random.Random(1))
            points[kind] = world.component_for_entity(e, CPoints).points
        self.assertEqual(points, {"I": 50, "P": 60, "E": 70})


CFG = {
    "deviation_degrees": {"easy": 60, "hard": 0},
    "spawn": {
        "interval_seconds": {"easy": 2.0, "hard": 0.5},
        "max_alive": {"easy": 100, "hard": 100},
        "distance": 150,
        "despawn_distance": 300,
    },
    "types": {
        "I": {"speed_factor": 1.2, "turn_rate": 180, "chase_seconds": 3.0, "points": 50,
              "spawn_weight": 1, "size": 8, "color": {"r": 255, "g": 255, "b": 0}},
        "P": {"speed_factor": 1.2, "turn_rate": 180, "chase_seconds": 1.0, "points": 60,
              "spawn_weight": 1, "wander": {"distance": 30, "radius": 20, "jitter": 720},
              "size": 8, "color": {"r": 0, "g": 255, "b": 255}},
        "E": {"speed_factor": 2.0, "points": 70, "spawn_weight": 1,
              "size": 8, "color": {"r": 255, "g": 0, "b": 255}},
    },
}


class EnemySpawnTests(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.rng = random.Random(3)
        self.player = pygame.Vector2(20, 1000)  # cerca del borde: el spawn cruza el mundo

    def spawn_for(self, seconds, difficulty=1.0, cfg=CFG):
        """Corre solo el spawner (los enemigos quedan donde nacen) y devuelve los enemigos."""
        create_enemy_spawner(self.world, cfg, difficulty)
        for _ in range(round(seconds / DT)):
            system_enemy_spawner(self.world, self.player, WORLD, cfg, PLAYER_SPEED, DT, self.rng)
        return [(c_t, c_v, c_s) for _, (c_t, c_v, c_s)
                in self.world.get_components(CTransform, CVelocity, CEnemyState)]

    def test_salen_fuera_de_la_pantalla_desde_todas_las_direcciones_rumbo_al_jugador(self):
        enemies = self.spawn_for(30.0)
        self.assertGreater(len(enemies), 40)
        quadrants = set()
        for c_t, c_v, _ in enemies:
            self.assertTrue(0 <= c_t.pos.x < WORLD.x and 0 <= c_t.pos.y < WORLD.y)
            from_player = wrap_delta(c_t.pos - self.player, WORLD)
            self.assertAlmostEqual(from_player.length(), 150, delta=0.01)
            # Nace apuntando al jugador.
            self.assertAlmostEqual(c_v.vel.normalize().dot(-from_player.normalize()), 1, places=5)
            quadrants.add((from_player.x > 0, from_player.y > 0))
        self.assertEqual(len(quadrants), 4)

    def test_salen_los_tres_tipos_al_azar(self):
        kinds = {c_s.kind for _, _, c_s in self.spawn_for(30.0)}
        self.assertEqual(kinds, {"I", "P", "E"})

    def test_con_mas_dificultad_salen_mas_enemigos(self):
        counts = []
        for difficulty in (0.0, 0.5, 1.0):
            self.world = esper.World()
            counts.append(len(self.spawn_for(10.1, difficulty)))
        self.assertEqual(counts[0], 5)    # uno cada 2 s
        self.assertEqual(counts[2], 20)   # uno cada 0.5 s
        self.assertTrue(counts[0] < counts[1] < counts[2])

    def test_no_pasa_del_tope_de_enemigos_vivos_que_sube_con_la_dificultad(self):
        cfg = dict(CFG, spawn=dict(CFG["spawn"], max_alive={"easy": 2, "hard": 6}))
        self.assertEqual(len(self.spawn_for(30.0, 0.0, cfg)), 2)
        self.world = esper.World()
        self.assertEqual(len(self.spawn_for(30.0, 1.0, cfg)), 6)

    def test_los_que_se_alejan_demasiado_desaparecen_y_dejan_sitio_a_otros(self):
        near = create_enemy(self.world, "I", pygame.Vector2(1000, 20), pygame.Vector2(1, 0),
                            CFG, PLAYER_SPEED, 1.0, self.rng)   # a ~28 px cruzando el borde
        far = create_enemy(self.world, "I", pygame.Vector2(400, 1000), pygame.Vector2(1, 0),
                           CFG, PLAYER_SPEED, 1.0, self.rng)    # a 380 px
        system_enemy_despawn(self.world, self.player, WORLD, CFG["spawn"]["despawn_distance"])
        self.assertTrue(self.world.entity_exists(near))
        self.assertFalse(self.world.entity_exists(far))

    def test_la_config_real_trae_el_spawn_fuera_de_la_pantalla(self):
        spawn = load_enemies()["spawn"]
        half_diagonal = pygame.Vector2(176, 208).length() / 2  # viewport de world.json
        self.assertGreater(spawn["distance"], half_diagonal)
        self.assertGreater(spawn["despawn_distance"], spawn["distance"])
        self.assertLess(spawn["interval_seconds"]["hard"], spawn["interval_seconds"]["easy"])


class EnemyConfigTests(unittest.TestCase):
    def load_with(self, change):
        """Carga una copia de enemies.json del repo modificada por `change`."""
        cfg = copy.deepcopy(load_enemies())
        change(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "enemies.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with mock.patch.object(data_loader, "CFG_DIR", tmp):
                return load_enemies()

    def test_sin_seccion_spawn_falla(self):
        with self.assertRaisesRegex(ConfigError, "spawn"):
            self.load_with(lambda cfg: cfg.pop("spawn"))

    def test_tipo_sin_puntos_falla(self):
        with self.assertRaisesRegex(ConfigError, "points"):
            self.load_with(lambda cfg: cfg["types"]["P"].pop("points"))

    def test_intervalo_cero_falla(self):
        with self.assertRaisesRegex(ConfigError, "interval_seconds"):
            self.load_with(lambda cfg: cfg["spawn"]["interval_seconds"].update(hard=0))

    def test_pesos_de_spawn_todos_en_cero_o_negativos_fallan(self):
        def all_zero(cfg):
            for t in cfg["types"].values():
                t["spawn_weight"] = 0
        with self.assertRaisesRegex(ConfigError, "spawn_weight"):
            self.load_with(all_zero)
        with self.assertRaisesRegex(ConfigError, "spawn_weight"):
            self.load_with(lambda cfg: cfg["types"]["I"].update(spawn_weight=-1))

    def test_tope_de_vivos_menor_que_uno_falla(self):
        with self.assertRaisesRegex(ConfigError, "max_alive"):
            self.load_with(lambda cfg: cfg["spawn"]["max_alive"].update(easy=0))

    def test_tipo_desconocido_falla(self):
        with self.assertRaisesRegex(ConfigError, "Z"):
            self.load_with(lambda cfg: cfg["types"].update(Z=dict(cfg["types"]["E"])))


class PlaySceneEnemyTests(unittest.TestCase):
    def setUp(self):
        # Los obstáculos del nivel se reparten al azar: con una semilla fija el jugador no
        # choca con uno antes del primer spawn (sin jugador vivo no salen enemigos).
        random.seed(1)
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene

    def enemies(self):
        return len(self.scene.world.get_component(CEnemyState))

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.do_update(DT)

    def test_no_salen_enemigos_durante_blast_off_ni_en_pausa(self):
        from src.engine.input.command import Phase
        self.run_for(self.engine.cfg_world["blast_off"]["seconds"] - 0.1)
        self.assertEqual(self.enemies(), 0)
        self.scene.blast_left = 0
        self.scene.do_action("PAUSE", Phase.START)
        self.run_for(30.0)
        self.assertEqual(self.enemies(), 0)

    def test_en_el_nivel_salen_enemigos_y_se_mueven(self):
        self.scene.blast_left = 0
        seen = 0
        for _ in range(20):  # los que se alejan desaparecen: se mira el máximo, no el final
            self.run_for(1.0)
            seen = max(seen, self.enemies())
        self.assertGreater(seen, 0)
        screen = pygame.Surface((256, 208))
        self.scene.do_draw(screen)  # dibujar con enemigos no falla


if __name__ == "__main__":
    unittest.main()
