"""Pruebas del comportamiento de las bases (#23): torretas que disparan y núcleo que se abre."""

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

from src.create.prefab_creator import create_base, create_enemy, create_enemy_bullet
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_enemy_bullet import CEnemyBullet
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_enemy_spawner import CEnemySpawner
from src.ecs.components.c_enemy_state import CEnemyState
from src.ecs.components.c_invulnerable import CInvulnerable
from src.ecs.systems.s_base_behavior import system_base_cores, system_turrets
from src.ecs.systems.s_base_damage import damage_base_part
from src.ecs.systems.s_enemy_bullet import system_enemy_bullets
from src.ecs.systems.s_movement import system_movement
from src.engine import data_loader
from src.engine.data_loader import ConfigError, load_bases, load_enemies, load_level
from src.engine.input.command import Phase
from src.engine.scenes import play_scene
from src.engine.game_engine import GameEngine

WORLD = pygame.Vector2(1024, 1024)
POS = pygame.Vector2(300, 400)
DT = 1 / 60
FAR = pygame.Vector2(800, 900)


class BehaviorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = GameEngine()  # deja listos la pantalla y el ServiceLocator
        cls.real_cfg = load_bases()

    @classmethod
    def tearDownClass(cls):
        cls.engine._clean()

    def setUp(self):
        self.world = esper.World()
        self.rng = random.Random(7)
        # Config real con tiempos conocidos para las pruebas.
        self.cfg = copy.deepcopy(self.real_cfg)
        self.cfg["turret"].update(range=100, warn_seconds=0.2,
                                  fire_interval={"min": 1.0, "max": 2.0})
        self.cfg["bullet"].update(speed=120, seconds=1.0)

    def parts(self, base, kind):
        return [ent for ent, c_p in self.world.get_component(CBasePart)
                if c_p.base == base and c_p.kind == kind]

    def image(self, base):
        """Cómo se ve la base dibujada sobre un fondo liso."""
        surf = self.world.component_for_entity(base, CSurface).surf
        screen = pygame.Surface(surf.get_size())
        screen.fill((9, 9, 9))
        screen.blit(surf, (0, 0))
        return pygame.image.tobytes(screen, "RGB")

    def bullets(self):
        return [(c_t, c_v) for _, (c_t, c_v, _c_b)
                in self.world.get_components(CTransform, CVelocity, CEnemyBullet)]


class TurretTests(BehaviorTestCase):
    def run_turrets(self, seconds, player):
        for _ in range(round(seconds / DT)):
            system_turrets(self.world, player, WORLD, self.cfg, DT)

    def test_lejos_del_jugador_siguen_cerradas_y_no_disparan(self):
        base = create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        closed = self.image(base)
        self.run_turrets(10.0, FAR)
        self.assertEqual(self.bullets(), [])
        self.assertEqual(self.image(base), closed)

    def test_cerca_del_jugador_se_abren_y_disparan_balas_hacia_el(self):
        base = create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        closed = self.image(base)
        player = POS + pygame.Vector2(0, 90)
        self.run_turrets(0.5, player)
        self.assertNotEqual(self.image(base), closed)  # abiertas
        self.assertEqual(self.bullets(), [])           # aún no les toca disparar
        self.run_turrets(1.6, player)
        bullets = self.bullets()
        self.assertGreaterEqual(len(bullets), 2)       # las dos de ese lado ya dispararon
        turret_pos = [tuple(self.world.component_for_entity(t, CTransform).pos)
                      for t in self.parts(base, "turret")]
        for c_t, c_v in bullets:
            self.assertAlmostEqual(c_v.vel.length(), 120, places=3)
            # Retrocediendo la bala se llega a una torreta, y apunta al jugador.
            origin = min(turret_pos, key=lambda p: (c_t.pos - p).cross(c_v.vel) ** 2)
            aim = (player - pygame.Vector2(origin)).normalize()
            self.assertAlmostEqual(c_v.vel.normalize().dot(aim), 1, places=3)

    def test_cada_torreta_dispara_a_su_propio_intervalo(self):
        base = create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        player = POS + pygame.Vector2(70, 70)  # del lado de tres torretas
        counts = []
        for _ in range(round(2.1 / DT)):
            system_turrets(self.world, player, WORLD, self.cfg, DT)
            counts.append(len(self.bullets()))
        # No salen las tres a la vez: la cuenta sube de una en una, en momentos distintos.
        self.assertTrue({0, 1, 2, 3} <= set(counts))
        self.assertEqual(len(self.parts(base, "turret")), 6)

    def test_solo_disparan_hacia_afuera_nunca_a_traves_de_la_base(self):
        base = create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        self.run_turrets(2.1, POS + pygame.Vector2(0, 90))  # el jugador está abajo
        self.assertGreaterEqual(len(self.bullets()), 2)
        for c_t, _ in self.bullets():
            # Todas salieron de las dos torretas de abajo (a 24 px del centro) y bajan.
            self.assertGreaterEqual(c_t.pos.y, POS.y + 24)
        self.assertEqual(len(self.parts(base, "turret")), 6)

    def test_al_alejarse_el_jugador_se_vuelven_a_cerrar(self):
        base = create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        closed = self.image(base)
        self.run_turrets(0.5, POS + pygame.Vector2(0, 90))
        self.assertNotEqual(self.image(base), closed)
        self.run_turrets(DT, FAR)
        self.assertEqual(self.image(base), closed)

    def test_el_alcance_cruza_el_borde_del_mundo(self):
        create_base(self.world, pygame.Vector2(1000, 500), "vertical", self.cfg, rng=self.rng)
        self.run_turrets(2.1, pygame.Vector2(60, 500))  # a 84 px cruzando el borde
        self.assertGreaterEqual(len(self.bullets()), 3)

    def test_una_torreta_destruida_no_dispara_ni_tapa_sus_restos(self):
        base = create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        for turret in self.parts(base, "turret")[1:]:
            damage_base_part(self.world, turret, pygame.Vector2(0, -1))
        self.run_turrets(2.1, POS + pygame.Vector2(-30, -80))  # del lado de la que queda
        self.assertIn(len(self.bullets()), (1, 2, 3))  # solo dispara esa

    def test_los_restos_de_una_torreta_abierta_son_iguales_a_los_de_una_cerrada(self):
        images = []
        for player in (FAR, POS + pygame.Vector2(0, 90)):
            self.world = esper.World()
            base = create_base(self.world, POS, "vertical", self.cfg, rng=random.Random(7))
            self.run_turrets(0.5, player)
            for turret in self.parts(base, "turret"):
                if len(self.parts(base, "turret")) > 1:
                    damage_base_part(self.world, turret, pygame.Vector2(0, -1))
            self.run_turrets(DT, FAR)  # la que queda vuelve a cerrarse
            images.append(self.image(base))
        self.assertEqual(images[0], images[1])


class EnemyBulletTests(BehaviorTestCase):
    def bullet(self, pos, vel=(0, 0)):
        return create_enemy_bullet(self.world, pygame.Vector2(pos), pygame.Vector2(vel),
                                   self.cfg["bullet"])

    def enemy(self, pos):
        return create_enemy(self.world, "I", pygame.Vector2(pos), pygame.Vector2(1, 0),
                            load_enemies(), 80, 0.5, self.rng)  # cuadro de 8 px

    def test_la_bala_desaparece_al_acabarse_su_tiempo(self):
        bullet = self.bullet((500, 500), (120, 0))
        for _ in range(round(0.9 / DT)):
            system_enemy_bullets(self.world, WORLD, DT)
        self.assertTrue(self.world.entity_exists(bullet))
        for _ in range(round(0.2 / DT)):
            system_enemy_bullets(self.world, WORLD, DT)
        self.assertFalse(self.world.entity_exists(bullet))

    def test_un_enemigo_que_choca_con_una_bala_muere_junto_con_ella(self):
        bullet = self.bullet((500, 500))
        hit = self.enemy((504, 497))    # su caja de 8 px toca la bala de 2 px
        missed = self.enemy((506, 500))  # a 6 px: no la toca
        system_enemy_bullets(self.world, WORLD, DT)
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertFalse(self.world.entity_exists(hit))
        self.assertTrue(self.world.entity_exists(missed))

    def test_una_bala_solo_se_lleva_a_un_enemigo(self):
        self.bullet((500, 500))
        self.enemy((503, 500))
        self.enemy((497, 500))
        system_enemy_bullets(self.world, WORLD, DT)
        self.assertEqual(len(self.world.get_component(CEnemyState)), 1)

    def test_el_choque_cruza_el_borde_del_mundo(self):
        bullet = self.bullet((1023, 500))
        enemy = self.enemy((2, 500))
        system_enemy_bullets(self.world, WORLD, DT)
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertFalse(self.world.entity_exists(enemy))

    def test_la_bala_de_una_torreta_mata_al_enemigo_que_se_cruza(self):
        create_base(self.world, POS, "vertical", self.cfg, rng=self.rng)
        player = POS + pygame.Vector2(0, 90)
        # Un muro de enemigos quietos entre la base y el jugador.
        for x in range(240, 364, 6):
            e = self.enemy((x, POS.y + 60))
            self.world.component_for_entity(e, CVelocity).vel = pygame.Vector2()
        before = len(self.world.get_component(CEnemyState))
        for _ in range(round(3.0 / DT)):
            system_turrets(self.world, player, WORLD, self.cfg, DT)
            system_movement(self.world, DT)
            system_enemy_bullets(self.world, WORLD, DT)
        self.assertLess(len(self.world.get_component(CEnemyState)), before)


UP, DOWN, LEFT, RIGHT = (pygame.Vector2(v) for v in ((0, -1), (0, 1), (-1, 0), (1, 0)))


class CoreTests(BehaviorTestCase):
    def setUp(self):
        super().setUp()
        # Ciclo: 2 s cerrado (4 s en fácil), 0.2 s abriendo, 1 s abierto, 0.2 s cerrando.
        self.cfg["core"].update(closed_seconds={"easy": 4.0, "hard": 2.0},
                                open_seconds=1.0, frame_seconds=0.1)
        self.cfg_enemies = load_enemies()
        self.player = POS + pygame.Vector2(40, 200)

    def run_cores(self, seconds):
        for _ in range(round(seconds / DT)):
            system_base_cores(self.world, self.player, WORLD, self.cfg_enemies, 80, DT)

    def enemies(self):
        return [(c_e.kind, c_t.pos, c_v.vel) for _, (c_t, c_v, c_e)
                in self.world.get_components(CTransform, CVelocity, CEnemyState)]

    def test_el_nucleo_siempre_abierto_no_cambia_ni_dispara(self):
        base = create_base(self.world, POS, "vertical", self.cfg, "open", rng=self.rng)
        opened = self.image(base)
        self.run_cores(20.0)
        self.assertEqual(self.image(base), opened)
        self.assertEqual(self.enemies(), [])
        self.assertEqual(damage_base_part(self.world, self.parts(base, "core")[0], UP), 1500)

    def test_el_nucleo_con_ciclo_se_cierra_y_se_vuelve_a_abrir(self):
        base = create_base(self.world, POS, "vertical", self.cfg, "cycle", 1.0, self.rng)
        opened = self.image(base)
        self.run_cores(1.0)
        closed = self.image(base)
        self.assertNotEqual(closed, opened)
        self.run_cores(1.1)             # t = 2.1: abriéndose
        self.assertNotIn(self.image(base), (closed, opened))
        self.run_cores(0.5)             # t = 2.6: abierto, igual al sprite original
        self.assertEqual(self.image(base), opened)
        self.run_cores(1.5)             # t = 4.1: otra vez cerrado (nuevo ciclo)
        self.assertEqual(self.image(base), closed)

    def test_al_abrirse_dispara_un_enemigo_e_hacia_el_lado_del_jugador(self):
        create_base(self.world, POS, "vertical", self.cfg, "cycle", 1.0, self.rng)
        self.run_cores(2.1)
        self.assertEqual(self.enemies(), [])    # todavía no termina de abrirse
        self.run_cores(0.5)
        (kind, pos, vel), = self.enemies()
        self.assertEqual(kind, "E")
        self.assertEqual(tuple(pos), tuple(POS))
        # Base vertical: sale por la abertura de abajo, donde está el jugador, sin desviarse.
        self.assertEqual(tuple(vel.normalize()), (0, 1))
        self.assertAlmostEqual(vel.length(), 80 * self.cfg_enemies["types"]["E"]["speed_factor"])
        self.run_cores(3.4)                     # un ciclo más: un E por apertura
        self.assertEqual(len(self.enemies()), 2)

    def test_la_base_horizontal_dispara_el_e_de_lado(self):
        create_base(self.world, POS, "horizontal", self.cfg, "cycle", 1.0, self.rng)
        self.player = POS + pygame.Vector2(-40, 200)
        self.run_cores(2.6)
        (_, _, vel), = self.enemies()
        self.assertEqual(tuple(vel.normalize()), (-1, 0))

    def test_el_nucleo_cerrado_no_recibe_dano(self):
        base = create_base(self.world, POS, "vertical", self.cfg, "cycle", 1.0, self.rng)
        core = self.parts(base, "core")[0]
        self.run_cores(1.0)
        self.assertEqual(damage_base_part(self.world, core, UP), 0)
        self.assertTrue(self.world.entity_exists(base))
        self.run_cores(1.6)
        self.assertEqual(damage_base_part(self.world, core, UP), 1500)

    def test_con_mas_dificultad_pasa_menos_tiempo_cerrado(self):
        create_base(self.world, POS, "vertical", self.cfg, "cycle", 0.0, self.rng)
        self.run_cores(3.0)
        self.assertEqual(self.enemies(), [])    # en fácil sigue cerrado
        self.run_cores(1.6)
        self.assertEqual(len(self.enemies()), 1)

    def test_una_base_destruida_deja_de_disparar(self):
        base = create_base(self.world, POS, "vertical", self.cfg, "cycle", 1.0, self.rng)
        for turret in self.parts(base, "turret"):
            damage_base_part(self.world, turret, UP)
        self.run_cores(10.0)
        self.assertEqual(self.enemies(), [])


class BehaviorConfigTests(unittest.TestCase):
    def load_bases_with(self, change):
        """Carga una copia de bases.json modificada por `change`."""
        cfg = copy.deepcopy(load_bases())
        change(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "bases.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with mock.patch.object(data_loader, "CFG_DIR", tmp):
                return load_bases()

    def load_level_with(self, change):
        """Carga una copia de level_01.json modificada por `change`."""
        level = copy.deepcopy(data_loader.load_json(data_loader.level_path(1)))
        change(level)
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "level_01.json"), "w", encoding="utf-8") as f:
                json.dump(level, f)
            with mock.patch.object(data_loader, "LEVELS_DIR", tmp):
                return load_level(1)

    def test_el_nivel_define_si_el_nucleo_queda_abierto_o_tiene_ciclo(self):
        self.assertEqual(load_level(1)["core_mode"], "open")
        self.assertEqual(self.load_level_with(lambda lv: lv.update(core_mode="cycle"))["core_mode"], "cycle")
        self.assertEqual(self.load_level_with(lambda lv: lv.pop("core_mode", None))["core_mode"], "open")
        with self.assertRaisesRegex(ConfigError, "core_mode"):
            self.load_level_with(lambda lv: lv.update(core_mode="cerrado"))

    def test_exige_los_datos_de_disparo_de_las_torretas(self):
        with self.assertRaisesRegex(ConfigError, "range"):
            self.load_bases_with(lambda cfg: cfg["turret"].pop("range"))
        with self.assertRaisesRegex(ConfigError, "bullet"):
            self.load_bases_with(lambda cfg: cfg.pop("bullet"))
        with self.assertRaisesRegex(ConfigError, "3 cuadros"):
            self.load_bases_with(lambda cfg: cfg["turret"]["frames"].pop())

    def test_el_intervalo_de_disparo_debe_ser_positivo_y_ordenado(self):
        with self.assertRaisesRegex(ConfigError, "fire_interval"):
            self.load_bases_with(lambda cfg: cfg["turret"]["fire_interval"].update(min=0))
        with self.assertRaisesRegex(ConfigError, "fire_interval"):
            self.load_bases_with(lambda cfg: cfg["turret"]["fire_interval"].update(min=9, max=1))

    def test_exige_el_ciclo_y_los_cuadros_del_nucleo(self):
        with self.assertRaisesRegex(ConfigError, "open_seconds"):
            self.load_bases_with(lambda cfg: cfg["core"].pop("open_seconds"))
        with self.assertRaisesRegex(ConfigError, "cuadros"):
            self.load_bases_with(lambda cfg: cfg["core"].update(frames=cfg["core"]["frames"][:1]))
        with self.assertRaisesRegex(ConfigError, "frame_seconds"):
            self.load_bases_with(lambda cfg: cfg["core"].update(frame_seconds=0))


class PlaySceneBehaviorTests(unittest.TestCase):
    def start(self, core):
        # Sin obstáculos: están repartidos al azar y la nave podría chocar con uno.
        level = dict(load_level(1), core_mode=core, obstacles={})
        with mock.patch.object(play_scene, "load_level", return_value=level):
            engine = GameEngine()
            self.addCleanup(engine._clean)
            engine._apply_scene_change("PLAY")
        self.scene = engine._current_scene
        self.scene.blast_left = 0
        # Sin enemigos del spawner: los que haya salieron de un núcleo.
        self.scene.cfg_enemies["spawn"]["interval_seconds"] = {"easy": 999, "hard": 999}
        for _, c_sp in self.scene.world.get_component(CEnemySpawner):
            c_sp.interval = 999
        return self.scene.world

    def run_for(self, seconds):
        for _ in range(round(seconds / DT)):
            self.scene.do_update(DT)

    def put_player(self, pos):
        # La nave avanza sola: se la deja quieta para que no se aleje de la posición dada.
        ship = self.scene.world.component_for_entity(self.scene.player, CPlayerShip)
        ship.speed = ship.max_speed = 0.0
        self.scene.world.component_for_entity(self.scene.player, CTransform).pos.update(pos)
        # Estas pruebas miden torretas y núcleos, no la muerte de la nave: las balas de la
        # base la alcanzarían y, sin nave, la IA de las bases se detiene.
        self.scene.world.add_component(self.scene.player, CInvulnerable())

    def test_las_torretas_disparan_al_jugador_cercano_y_las_balas_avanzan_y_caducan(self):
        world = self.start("open")
        self.put_player((300, 470))  # junto a la base de (300, 400)
        self.run_for(4.0)
        bullets = world.get_component(CEnemyBullet)
        self.assertGreater(len(bullets), 0)
        self.scene.do_draw(pygame.Surface((256, 208)))  # dibujar con balas no falla
        self.put_player((900, 900))  # lejos de todas las bases: no salen más
        self.run_for(load_bases()["bullet"]["seconds"] + 0.1)
        self.assertEqual(world.get_component(CEnemyBullet), [])
        self.assertEqual(world.get_component(CEnemyState), [])  # núcleo abierto: no dispara

    def test_en_un_nivel_con_ciclo_el_nucleo_lanza_enemigos_e(self):
        world = self.start("cycle")
        self.put_player((300, 470))
        seen = set()
        for _ in range(12):
            self.run_for(1.0)
            seen.update(c_e.kind for _, c_e in world.get_component(CEnemyState))
        self.assertEqual(seen, {"E"})  # las balas de su propia base no lo alcanzan al salir

    def test_en_pausa_las_bases_no_disparan(self):
        world = self.start("cycle")
        self.put_player((300, 470))
        self.scene.do_action("PAUSE", Phase.START)
        self.run_for(15.0)
        self.assertEqual(world.get_component(CEnemyBullet), [])
        self.assertEqual(world.get_component(CEnemyState), [])


if __name__ == "__main__":
    unittest.main()
