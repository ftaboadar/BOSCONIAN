"""Pruebas de la IA de enemigos (#20): patrón State por tipo y steering behaviours."""

import os
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import create_enemy
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.camera import wrap_delta
from src.engine.data_loader import load_enemies, load_entity_cfg

WORLD = pygame.Vector2(1024, 1024)
PLAYER_SPEED = 80
DT = 1 / 60

SPRITE = {"x": 0, "y": 111, "w": 14, "h": 14}  # una nave de naves.png

CFG = {
    "deviation_degrees": {"easy": 60, "hard": 0},
    "types": {
        "I": {"speed_factor": 1.2, "turn_rate": 180, "chase_seconds": 3.0, "points": 50,
              "sprite": SPRITE},
        "P": {"speed_factor": 1.2, "turn_rate": 180, "chase_seconds": 1.0, "points": 60,
              "wander": {"distance": 30, "radius": 20, "jitter": 720},
              "sprite": SPRITE},
        "E": {"speed_factor": 2.0, "points": 70, "sprite": SPRITE},
    },
}


def angle_between(a, b):
    """Ángulo absoluto entre dos vectores, en grados (0..180)."""
    return abs((a.angle_to(b) + 180) % 360 - 180)


class EnemyAITests(unittest.TestCase):
    def setUp(self):
        self.world = esper.World()
        self.rng = random.Random(1)

    def enemy(self, kind, pos, direction, difficulty=1.0, cfg=CFG):
        return create_enemy(self.world, kind, pygame.Vector2(pos), pygame.Vector2(direction),
                            cfg, PLAYER_SPEED, difficulty, self.rng)

    def step(self, player_pos, seconds):
        for _ in range(round(seconds / DT)):
            system_enemy_state(self.world, pygame.Vector2(player_pos), WORLD, DT, self.rng)
            system_movement(self.world, DT)
            system_wraparound(self.world, WORLD)

    def test_tipo_i_empieza_persiguiendo_y_gira_hacia_el_jugador(self):
        e = self.enemy("I", (500, 500), (0, -1))  # mira hacia arriba
        self.step((600, 500), 1.0)  # el jugador está a la derecha
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state, EnemyState.CHASE)
        pos = self.world.component_for_entity(e, CTransform).pos
        vel = self.world.component_for_entity(e, CVelocity).vel
        self.assertLess(angle_between(vel, wrap_delta(pygame.Vector2(600, 500) - pos, WORLD)), 1)

    def test_tipo_i_se_va_despues_de_un_rato(self):
        e = self.enemy("I", (500, 500), (1, 0))
        self.step((600, 500), 2.9)
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state, EnemyState.CHASE)
        self.step((600, 500), 0.2)  # pasan los 3 s de persecución
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state, EnemyState.LEAVE)
        self.step((600, 500), 1.5)  # le da tiempo de dar la vuelta
        vel = self.world.component_for_entity(e, CVelocity).vel
        pos = self.world.component_for_entity(e, CTransform).pos
        away = wrap_delta(pos - pygame.Vector2(600, 500), WORLD)
        self.assertLess(angle_between(vel, away), 5)  # huye del jugador

    def test_tipo_p_persigue_y_pronto_se_vuelve_aleatorio(self):
        e = self.enemy("P", (500, 500), (1, 0))
        self.step((600, 500), 0.5)
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state, EnemyState.CHASE)
        self.step((600, 500), 0.6)  # pasa 1 s de persecución
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state, EnemyState.WANDER)
        headings = []
        for _ in range(8):
            self.step((600, 500), 0.5)
            headings.append(pygame.Vector2(self.world.component_for_entity(e, CVelocity).vel))
        turns = [angle_between(a, b) for a, b in zip(headings, headings[1:])]
        self.assertGreater(max(turns), 10)  # deambula: no va en línea recta
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state, EnemyState.WANDER)

    def test_tipo_e_va_derecho_sin_desviarse(self):
        e = self.enemy("E", (500, 500), (0, -1))
        self.step((600, 500), 3.0)  # el jugador está a la derecha y no le importa
        self.assertEqual(self.world.component_for_entity(e, CEnemyState).state,
                         EnemyState.STRAIGHT)
        vel = self.world.component_for_entity(e, CVelocity).vel
        self.assertEqual((vel.x, vel.y), (0, -PLAYER_SPEED * 2.0))

    def test_velocidad_constante_y_mayor_que_la_del_jugador_con_la_config_real(self):
        cfg = load_enemies()
        player_speed = load_entity_cfg("player", ("max_speed",))["max_speed"]
        enemies = [create_enemy(self.world, kind, pygame.Vector2(500, 500), pygame.Vector2(0, -1),
                                cfg, player_speed, 0.5, self.rng) for kind in ("I", "P", "E")]
        for _ in range(20):  # 10 s: pasan por todos sus estados
            self.step((600, 500), 0.5)
            for e in enemies:
                speed = self.world.component_for_entity(e, CVelocity).vel.length()
                self.assertGreater(speed, player_speed)

    def test_sin_direccion_inicial_igual_sale_a_su_velocidad(self):
        e = self.enemy("E", (500, 500), (0, 0))
        self.assertAlmostEqual(self.world.component_for_entity(e, CVelocity).vel.length(), 160)

    def mean_chase_distance(self, difficulty, seconds=3.0, cfg=CFG, player_speed=0.0):
        """Distancia media al jugador de 16 enemigos I mientras lo persiguen.

        Con `player_speed` el jugador avanza y gira 90 grados cada 3 s, como en el juego.
        """
        self.world = esper.World()
        self.rng = random.Random(7)
        player = pygame.Vector2(512, 512)
        player_vel = pygame.Vector2(player_speed, 0)
        enemies = []
        for i in range(16):
            out = pygame.Vector2(200, 0).rotate(i * 360 / 16)
            enemies.append(self.enemy("I", player + out, -out, difficulty, cfg))
            self.world.component_for_entity(enemies[-1], CEnemyState).chase_seconds = seconds
        total, samples = 0.0, 0
        for frame in range(round(seconds / DT)):
            if frame and frame % round(3 / DT) == 0:
                player_vel.rotate_ip(90)
            player = pygame.Vector2((player.x + player_vel.x * DT) % WORLD.x,
                                    (player.y + player_vel.y * DT) % WORLD.y)
            self.step(player, DT)
            if frame % 6 == 0:
                for e in enemies:
                    total += wrap_delta(self.world.component_for_entity(e, CTransform).pos
                                        - player, WORLD).length()
                    samples += 1
        return total / samples

    def test_con_mas_dificultad_se_acercan_mas_y_con_menos_se_desvian_mas(self):
        easy = self.mean_chase_distance(0.0)
        medium = self.mean_chase_distance(0.5)
        hard = self.mean_chase_distance(1.0)
        self.assertLess(hard, medium)
        self.assertLess(medium, easy)

    def test_persiguiendo_a_un_jugador_que_se_mueve_la_dificultad_se_nota_con_la_config_real(self):
        # Con mucho desvío no alcanzan al jugador; con poco se le pegan (comportamiento emergente).
        cfg = load_enemies()
        player_speed = load_entity_cfg("player", ("max_speed",))["max_speed"]
        easy = self.mean_chase_distance(0.0, 10.0, cfg, player_speed)
        medium = self.mean_chase_distance(0.5, 10.0, cfg, player_speed)
        hard = self.mean_chase_distance(1.0, 10.0, cfg, player_speed)
        self.assertLess(hard, medium)
        self.assertLess(medium, easy)

if __name__ == "__main__":
    unittest.main()
