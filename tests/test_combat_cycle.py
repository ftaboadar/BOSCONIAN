"""Integración del ciclo de combate (#71): disparar, colisionar, explotar, puntuar y morir.

Todas las pruebas usan una escena de nivel real (jugador, bases, enemigos, balas, colisiones
y explosiones juntos), no sistemas sueltos: lo que se comprueba es que conviven y que el orden
de ejecución de do_update produce el resultado esperado.
"""

import os
import random
import sys
import unittest
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.create.prefab_creator import (create_base, create_enemy, create_enemy_bullet,
                                       create_player_bullet)
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_base_core import CBaseCore
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_enemy_bullet import CEnemyBullet
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState, EnemyState
from src.ecs.components.c_invulnerable import CInvulnerable
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_player_bullet import CPlayerBullet
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.engine.data_loader import load_bases, load_enemies, load_level
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase
from src.engine.scenes import play_scene

DT = 1 / 60
BASE_POS = pygame.Vector2(300, 400)
UP = pygame.Vector2(0, -1)


class CombatCycleTestCase(unittest.TestCase):
    """Nivel 1 sin obstáculos, con una sola base y sin enemigos del spawner."""

    orientation = "vertical"
    core_mode = "open"
    with_base = True

    def setUp(self):
        random.seed(3)
        level = dict(load_level(1), obstacles={}, core_mode=self.core_mode, special_shot=False,
                     bases=[] if not self.with_base else
                     [{"x": BASE_POS.x, "y": BASE_POS.y, "orientation": self.orientation}])
        with mock.patch.object(play_scene, "load_level", return_value=level):
            self.engine = GameEngine()
            self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.scene.blast_left = 0
        self.world = self.scene.world
        self.state = self.engine.state
        for _, c_sp in self.world.get_component(CEnemySpawner):
            c_sp.interval = 9999  # los únicos enemigos son los que pone cada prueba
        self.player = self.scene.player
        self.world.component_for_entity(self.player, CTransform).pos.update(512, 512)
        self.scene.camera.follow(pygame.Vector2(512, 512))

    # --- ayudas -------------------------------------------------------------------------

    def step(self, seconds=DT):
        for _ in range(max(1, round(seconds / DT))):
            self.scene.do_update(DT)

    def step_until_scene_change(self, max_seconds=5.0):
        """Avanza como el motor: al pedirse otra escena ya no se vuelve a actualizar esta."""
        for _ in range(round(max_seconds / DT)):
            self.scene.do_update(DT)
            if self.engine._next_scene is not None:
                return self.engine._next_scene
        return None

    def park_player(self, pos):
        """Deja la nave quieta en `pos` y la cámara sobre ella (la nave avanza sola si no)."""
        ship = self.world.component_for_entity(self.player, CPlayerShip)
        ship.speed = ship.max_speed = 0.0
        self.world.component_for_entity(self.player, CTransform).pos.update(pos[0], pos[1])
        self.scene.camera.follow(pygame.Vector2(pos))

    def alive(self, ent):
        return self.world.entity_exists(ent)

    def parts(self, kind):
        return [e for e, c in self.world.get_component(CBasePart) if c.kind == kind]

    def explosions(self):
        return [e for e, _ in self.world.get_component(CAnimation)]

    def still_enemy(self, kind, pos):
        """Enemigo quieto (sin velocidad) para que la prueba no dependa de su IA."""
        enemy = create_enemy(self.world, kind, pygame.Vector2(pos), UP, self.scene.cfg_enemies,
                             self.scene.player_speed, 0.0)
        self.world.component_for_entity(enemy, CVelocity).vel = pygame.Vector2()
        self.world.component_for_entity(enemy, CEnemyState).state = EnemyState.STRAIGHT  # sin steering
        return enemy

    def bullet(self, pos, vel):
        return create_player_bullet(self.world, pygame.Vector2(pos), pygame.Vector2(vel),
                                    pygame.Surface((4, 4)))


class PlayerShotsTests(CombatCycleTestCase):
    with_base = False

    def test_disparar_destruye_al_enemigo_lo_hace_explotar_y_suma_sus_puntos(self):
        enemy = self.still_enemy("I", (512, 480))     # 32 px delante de la nave (rumbo: arriba)
        points = load_enemies()["types"]["I"]["points"]
        self.world.add_component(self.player, CInvulnerable())  # no hay choques: solo se mide el disparo
        self.scene.do_action("FIRE", Phase.START)
        self.step(0.6)
        self.assertFalse(self.alive(enemy))
        self.assertEqual(self.state.score, points)
        self.assertEqual(self.state.hi_score, max(self.state.cfg["hi_score"], points))

    def test_el_enemigo_explota_con_una_animacion_en_su_posicion(self):
        enemy = self.still_enemy("P", (700, 700))
        pos = pygame.Vector2(self.world.component_for_entity(enemy, CTransform).pos)
        self.bullet(pos, (0, 0))
        self.step(DT)
        self.assertFalse(self.alive(enemy))
        (boom,) = self.explosions()
        self.assertLess(self.world.component_for_entity(boom, CTransform).pos.distance_to(pos), 1.0)
        self.step(2.0)  # la animación no se repite: al terminar desaparece
        self.assertEqual(self.explosions(), [])

    def test_cada_tipo_de_enemigo_da_sus_puntos(self):
        for kind in ("I", "P", "E"):
            before = self.state.score
            self.still_enemy(kind, (800, 300))
            self.bullet((800, 300), (0, 0))
            self.step(DT)
            self.assertEqual(self.state.score - before, load_enemies()["types"][kind]["points"], kind)

    def test_la_bala_se_consume_al_impactar(self):
        self.still_enemy("I", (700, 700))
        bullet = self.bullet((700, 700), (0, 0))
        self.step(DT)
        self.assertFalse(self.alive(bullet))

    def test_una_bala_que_no_toca_nada_no_puntua(self):
        self.bullet((900, 900), (0, 0))
        self.step(0.5)
        self.assertEqual(self.state.score, 0)


class PlayerDeathTests(CombatCycleTestCase):
    with_base = False

    def test_la_bala_enemiga_mata_al_jugador_y_cuesta_una_vida(self):
        lives = self.state.lives
        create_enemy_bullet(self.world, pygame.Vector2(512, 512), pygame.Vector2(),
                            load_bases()["bullet"])
        self.step(DT)
        self.assertFalse(self.alive(self.player))
        self.assertEqual(len(self.world.get_component(CEnemyBullet)), 0)  # la bala también muere
        self.assertEqual(self.step_until_scene_change(), "PLAY")  # tras ver la explosión, repite
        self.assertEqual(self.state.lives, lives - 1)

    def test_chocar_con_un_enemigo_mata_a_los_dos(self):
        enemy = self.still_enemy("I", (512, 512))
        self.step(DT)
        self.assertFalse(self.alive(self.player))
        self.assertFalse(self.alive(enemy))
        self.assertEqual(self.state.score, 0)  # matar embistiendo no puntúa

    def test_en_modo_trampa_la_nave_sobrevive_pero_el_enemigo_no(self):
        self.world.add_component(self.player, CInvulnerable())
        enemy = self.still_enemy("I", (512, 512))
        self.step(DT)
        self.assertTrue(self.alive(self.player))
        self.assertFalse(self.alive(enemy))

    def test_ultima_vida_lleva_a_la_derrota(self):
        self.state.lives = 0
        create_enemy_bullet(self.world, pygame.Vector2(512, 512), pygame.Vector2(),
                            load_bases()["bullet"])
        self.assertEqual(self.step_until_scene_change(), "DEFEAT")


class BaseDamageTests(CombatCycleTestCase):
    def test_cada_torreta_destruida_da_200_y_la_sexta_se_lleva_la_base(self):
        turrets = self.parts("turret")
        self.assertEqual(len(turrets), 6)
        total = 0
        for i, turret in enumerate(turrets):
            pos = self.world.component_for_entity(turret, CTransform).pos
            self.bullet(pos, (0, 0))
            self.step(DT)
            self.assertFalse(self.alive(turret))
            total = self.state.score
            if i < 5:
                self.assertEqual(total, 200 * (i + 1), f"torreta {i + 1}")
        self.assertEqual(total, 6 * 200 + 1500)
        self.assertEqual(self.parts("turret") + self.parts("core"), [])  # la base y sus partes cayeron

    def test_la_base_destruida_explota_y_el_nivel_termina(self):
        for turret in self.parts("turret"):
            self.bullet(self.world.component_for_entity(turret, CTransform).pos, (0, 0))
            self.step(DT)
        self.assertEqual([t for _, t in self.world.get_component(CMinimapTrack) if t.kind == "base"], [])
        self.assertTrue(len(self.explosions()) >= self.scene.explosions_cfg["base"]["count"])
        self.assertIsNotNone(self.engine._next_scene)  # siguiente nivel o victoria

    def test_un_disparo_al_nucleo_abierto_destruye_la_base_entera(self):
        core = self.parts("core")[0]
        pos = self.world.component_for_entity(core, CTransform).pos
        self.bullet(pos + pygame.Vector2(0, 10), (0, -220))  # base vertical: se entra por arriba/abajo
        self.step(0.2)
        self.assertEqual(self.state.score, 1500)
        self.assertEqual(self.parts("turret") + self.parts("core"), [])

    def test_un_disparo_perpendicular_al_nucleo_no_hace_nada(self):
        core = self.parts("core")[0]
        pos = self.world.component_for_entity(core, CTransform).pos
        self.bullet(pos, (220, 0))  # la base vertical solo es vulnerable en vertical
        self.step(DT)
        self.assertTrue(self.alive(core))
        self.assertEqual(self.state.score, 0)

    def test_dos_balas_en_el_mismo_fotograma_sobre_una_torreta_puntuan_una_vez(self):
        turret = self.parts("turret")[0]
        pos = self.world.component_for_entity(turret, CTransform).pos
        self.bullet(pos, (0, 0))
        self.bullet(pos, (0, 0))
        self.step(DT)
        self.assertEqual(self.state.score, 200)

    def test_chocar_con_la_base_mata_a_la_nave_pero_no_a_la_base(self):
        self.park_player((BASE_POS.x, BASE_POS.y + 30))  # dentro de la hitbox (mitad del alto: 32)
        self.step(DT)
        self.assertFalse(self.alive(self.player))
        self.assertTrue(self.parts("core"))

    def test_las_balas_pasan_sobre_el_cuerpo_de_la_base_sin_tocar_partes(self):
        self.park_player((BASE_POS.x, BASE_POS.y + 70))  # cámara cerca (sin tocar la base): la bala no sale de pantalla
        bullet = self.bullet(BASE_POS + pygame.Vector2(20, 12), (0, 0))  # entre torretas y núcleo
        self.step(DT)
        self.assertTrue(self.alive(bullet))
        self.assertEqual(self.state.score, 0)


class HorizontalBaseTests(CombatCycleTestCase):
    orientation = "horizontal"

    def test_la_base_horizontal_es_vulnerable_por_los_lados(self):
        core = self.parts("core")[0]
        pos = self.world.component_for_entity(core, CTransform).pos
        self.bullet(pos + pygame.Vector2(12, 0), (-220, 0))
        self.step(0.2)
        self.assertEqual(self.state.score, 1500)


class CyclingCoreTests(CombatCycleTestCase):
    core_mode = "cycle"

    def test_el_nucleo_cerrado_detiene_la_bala_sin_dano(self):
        core = self.parts("core")[0]
        self.step(DT)  # el sprite trae el núcleo abierto: el primer cuadro del ciclo lo cierra
        self.assertEqual(self.world.component_for_entity(core, CBaseCore).frame, 0)
        pos = self.world.component_for_entity(core, CTransform).pos
        bullet = self.bullet(pos, (0, -220))
        self.step(DT)
        self.assertTrue(self.alive(core))
        self.assertFalse(self.alive(bullet))
        self.assertEqual(self.state.score, 0)

    def test_el_enemigo_que_sale_del_nucleo_no_se_queda_atrapado_en_la_base(self):
        self.park_player((BASE_POS.x, BASE_POS.y + 200))  # debajo de la base: el E sale hacia abajo
        self.world.add_component(self.player, CInvulnerable())
        seen = None
        for _ in range(round(12.0 / DT)):
            self.scene.do_update(DT)
            es = [e for e, s in self.world.get_component(CEnemyState) if s.kind == "E"]
            if es:
                seen = es[0]
                break
        self.assertIsNotNone(seen, "el núcleo no lanzó ningún E")
        y0 = self.world.component_for_entity(seen, CTransform).pos.y
        self.step(1.0)
        if self.alive(seen):
            self.assertGreater(self.world.component_for_entity(seen, CTransform).pos.y, y0 + 20)


class FullCycleTests(CombatCycleTestCase):
    def test_partida_corrida_con_todo_activo_no_falla_y_dibuja(self):
        """Disparar sin parar durante 40 s con enemigos, torretas y colisiones activos."""
        for _, c_sp in self.world.get_component(CEnemySpawner):
            c_sp.interval = 2.0
        self.world.add_component(self.player, CInvulnerable())
        self.scene.do_action("FIRE", Phase.START)
        screen = pygame.Surface((256, 208))
        for i in range(round(40.0 / DT)):
            self.scene.do_update(DT)
            if i % 120 == 0:
                self.scene.do_draw(screen)
            if self.engine._next_scene is not None:
                break
        self.assertGreaterEqual(self.state.score, 0)
        self.assertLessEqual(len(self.world.get_component(CPlayerBullet)), 200)

    def test_las_colisiones_corren_antes_que_la_limpieza_de_entidades(self):
        """Una entidad marcada en el frame ya no existe al terminar do_update (explota y se borra)."""
        enemy = self.still_enemy("E", (700, 700))
        self.bullet((700, 700), (0, 0))
        self.step(DT)
        self.assertFalse(self.alive(enemy))
        self.assertEqual(len(self.world.get_component(CEnemyState)), 0)


if __name__ == "__main__":
    unittest.main()
