"""Pruebas de la revisión final: toda colisión deja una explosión, las balas no atraviesan las
rocas indestructibles, la base choca solo donde hay base, morir al caer la última base cuesta
la vida y las cuentas del nivel y el input de la nave son sistemas ECS."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import (create_base, create_enemy_bullet, create_level_clock,
                                       create_player, create_player_bullet)
from src.create.prefab_obstacles import create_solid_rock
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_enemy_bullet import CEnemyBullet
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_level_clock import CLevelClock
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_player_bullet import CPlayerBullet
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_weapon import CWeapon
from src.ecs.systems.s_base_damage import damage_base_part, system_bases_destroyed
from src.ecs.systems.s_collision import hitbox_rect, system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_explode import system_explode
from src.ecs.systems.s_level import system_blast_off, system_player_death
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_player import system_player_input
from src.engine.data_loader import load_bases, load_json
from src.engine.game_engine import GameEngine
from src.engine.input.command import Phase

WORLD = pygame.Vector2(1024, 1024)
COLLISIONS = load_json("assets/cfg/collisions.json")
EXPLOSIONS = load_json("assets/cfg/explosions.json")
OBSTACLES = load_json("assets/cfg/obstacles.json")
RULES = load_rules(COLLISIONS)
POS = pygame.Vector2(300, 400)
DT = 1 / 60


class EcsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = GameEngine()  # carga imágenes, sonidos y fuentes

    def setUp(self):
        self.world = esper.World()

    def frame(self) -> int:
        """Colisiones, reglas, explosiones y borrado: el final de un frame del nivel."""
        points = system_collision_rules(self.world, system_collision(self.world, WORLD), RULES, WORLD)
        system_explode(self.world, EXPLOSIONS)
        system_destroy(self.world)
        return points

    def explosions(self) -> int:
        return len(self.world.get_component(CAnimation))


class BulletsAgainstSolidRockTests(EcsTestCase):
    def setUp(self):
        super().setUp()
        self.rock = create_solid_rock(self.world, POS, OBSTACLES["solid_rock"])

    def test_la_bala_enemiga_se_destruye_contra_la_roca_indestructible(self):
        bullet = create_enemy_bullet(self.world, POS, pygame.Vector2(100, 0), load_bases()["bullet"])
        self.frame()
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertTrue(self.world.entity_exists(self.rock))

    def test_las_balas_explotan_al_chocar_con_la_roca(self):
        makers = (lambda: create_enemy_bullet(self.world, POS, pygame.Vector2(100, 0),
                                              load_bases()["bullet"]),
                  lambda: create_player_bullet(self.world, POS, pygame.Vector2(100, 0),
                                               pygame.Surface((2, 2))))
        for make in makers:
            before = self.explosions()
            make()
            self.frame()
            self.assertEqual(self.explosions(), before + 1)
        self.assertEqual(self.world.get_component(CEnemyBullet), [])
        self.assertEqual(self.world.get_component(CPlayerBullet), [])

    def test_la_explosion_del_impacto_no_sale_volando_con_la_bala(self):
        create_player_bullet(self.world, POS, pygame.Vector2(300, 0), pygame.Surface((2, 2)))
        self.frame()
        ((_, (_c_a, c_t)),) = self.world.get_components(CAnimation, CTransform)
        self.assertEqual(tuple(c_t.pos), tuple(POS))
        ((_, (_c_a, c_v)),) = self.world.get_components(CAnimation, CVelocity)
        self.assertEqual(tuple(c_v.vel), (0, 0))


class DestroyWithoutExplosionTests(EcsTestCase):
    def test_lo_que_agota_su_tiempo_pasa_por_cdestroy_y_no_explota(self):
        bullet = create_enemy_bullet(self.world, POS, pygame.Vector2(), load_bases()["bullet"])
        self.world.component_for_entity(bullet, CLifetime).remaining = 0.01
        system_lifetime(self.world, DT)
        self.assertTrue(self.world.entity_exists(bullet))  # marcada, aún no borrada
        self.assertFalse(self.world.component_for_entity(bullet, CDestroy).explodes)
        system_explode(self.world, EXPLOSIONS)
        system_destroy(self.world)
        self.assertFalse(self.world.entity_exists(bullet))
        self.assertEqual(self.explosions(), 0)


class TurretExplosionTests(EcsTestCase):
    def test_una_torreta_destruida_explota_donde_estaba(self):
        base = create_base(self.world, POS, "vertical", load_bases())
        turret, c_t = next((e, self.world.component_for_entity(e, CTransform))
                           for e, c_p in self.world.get_component(CBasePart) if c_p.kind == "turret")
        where = tuple(c_t.pos)
        damage_base_part(self.world, turret, pygame.Vector2(0, -1))
        system_explode(self.world, EXPLOSIONS)
        system_destroy(self.world)
        self.assertFalse(self.world.entity_exists(turret))
        self.assertTrue(self.world.entity_exists(base))
        ((_, (_c_a, c_e)),) = self.world.get_components(CAnimation, CTransform)
        self.assertEqual(tuple(c_e.pos), where)


class BasesDestroyedSystemTests(EcsTestCase):
    def core(self, base):
        return next(e for e, c_p in self.world.get_component(CBasePart)
                    if c_p.base == base and c_p.kind == "core")

    def test_devuelve_el_indice_de_la_base_que_cae_en_el_frame(self):
        cfg = load_bases()
        create_base(self.world, POS, "vertical", cfg, index=0)
        second = create_base(self.world, pygame.Vector2(700, 700), "vertical", cfg, index=3)
        self.assertEqual(system_bases_destroyed(self.world), [])
        damage_base_part(self.world, self.core(second), pygame.Vector2(0, -1))
        self.assertEqual(system_bases_destroyed(self.world), [3])
        system_destroy(self.world)
        self.assertEqual(system_bases_destroyed(self.world), [])
        self.assertEqual([c_b.index for _, c_b in self.world.get_component(CBase)], [0])


class BaseBodyHitboxTests(EcsTestCase):
    def body(self, base):
        return [(self.world.component_for_entity(e, CTransform), self.world.component_for_entity(e, CHitBox))
                for e, c_p in self.world.get_component(CBasePart) if c_p.base == base and c_p.kind == "body"]

    def player_dies_at(self, base_pos, offset) -> bool:
        world = self.world = esper.World()
        create_base(world, base_pos, self.orientation, load_bases())
        player = create_player(world, base_pos + pygame.Vector2(offset), load_json("assets/cfg/player.json"))
        self.frame()
        return not world.entity_exists(player)

    def test_las_piezas_cubren_base_y_no_los_huecos(self):
        """Cada pieza cae sobre píxeles de la base, y casi toda la base queda cubierta."""
        for orientation in ("vertical", "horizontal"):
            with self.subTest(orientation=orientation):
                self.world = esper.World()
                base = create_base(self.world, POS, orientation, load_bases())
                surf = self.world.component_for_entity(base, CSurface).surf
                origin = POS - pygame.Vector2(surf.get_size()) / 2
                rects = [hitbox_rect(c_t, c_hb).move(-origin.x, -origin.y) for c_t, c_hb in self.body(base)]
                self.assertEqual(len(rects), len(COLLISIONS["hitboxes"]["base"]["boxes"]))
                w, h = surf.get_size()
                solid = {(x, y) for x in range(w) for y in range(h) if surf.get_at((x, y)).a}
                boxed = {(x, y) for x in range(w) for y in range(h)
                         if any(r.collidepoint(x + 0.5, y + 0.5) for r in rects)}
                self.assertGreater(len(boxed & solid) / len(boxed), 0.75)  # poco vacío dentro de las cajas
                self.assertGreater(len(boxed & solid) / len(solid), 0.85)  # poca base sin caja
                self.assertTrue(all(pygame.Rect(0, 0, w, h).contains(pygame.Rect(r)) for r in rects))

    def test_las_esquinas_vacias_del_sprite_ya_no_matan(self):
        for orientation, corner in (("vertical", (-30, -26)), ("horizontal", (-26, -30))):
            self.orientation = orientation
            with self.subTest(orientation=orientation):
                self.assertFalse(self.player_dies_at(POS, corner))
                self.assertFalse(self.player_dies_at(POS, (-corner[0], -corner[1])))

    def test_chocar_con_una_torreta_o_con_el_nucleo_sigue_matando(self):
        self.orientation = "vertical"
        for offset in ((-12, -24), (28, 0), (0, 0), (-21, -13)):
            with self.subTest(offset=offset):
                self.assertTrue(self.player_dies_at(POS, offset))

    def test_las_piezas_desaparecen_con_la_base(self):
        create_base(self.world, POS, "vertical", load_bases())
        core = next(e for e, c_p in self.world.get_component(CBasePart) if c_p.kind == "core")
        damage_base_part(self.world, core, pygame.Vector2(0, -1))
        system_explode(self.world, EXPLOSIONS)
        system_destroy(self.world)
        self.assertEqual(self.world.get_component(CBasePart), [])
        self.assertEqual(self.world.get_component(CHitBox), [])
        self.assertEqual(self.explosions(), EXPLOSIONS["base"]["count"])  # solo la de la base


class LevelClockTests(EcsTestCase):
    def setUp(self):
        super().setUp()
        self.clock = self.world.component_for_entity(create_level_clock(self.world, 1.0, 0.5), CLevelClock)

    def test_blast_off_cuenta_y_termina(self):
        self.assertTrue(system_blast_off(self.world, 0.6))
        self.assertAlmostEqual(self.clock.blast_left, 0.4)
        self.assertTrue(system_blast_off(self.world, 0.6))  # el frame en que llega a cero aún no se juega
        self.assertEqual(self.clock.blast_left, 0.0)
        self.assertFalse(system_blast_off(self.world, 0.6))

    def test_con_nave_no_hay_espera_y_sin_nave_avisa_al_terminar(self):
        ship = create_player(self.world, POS, load_json("assets/cfg/player.json"))
        self.assertFalse(system_player_death(self.world, 1.0))
        self.assertIsNone(self.clock.death_left)
        self.world.delete_entity(ship, immediate=True)
        self.assertFalse(system_player_death(self.world, 0.3))
        self.assertAlmostEqual(self.clock.death_left, 0.2)
        self.assertTrue(system_player_death(self.world, 0.3))


class PlayerInputSystemTests(EcsTestCase):
    def setUp(self):
        super().setUp()
        ship = create_player(self.world, POS, load_json("assets/cfg/player.json"))
        self.ship = self.world.component_for_entity(ship, CPlayerShip)
        self.weapon = self.world.component_for_entity(ship, CWeapon)

    def test_las_direcciones_se_guardan_y_se_sueltan(self):
        system_player_input(self.world, "UP", Phase.START, True, True)
        system_player_input(self.world, "LEFT", Phase.START, True, True)
        self.assertEqual(self.ship.held, {"UP", "LEFT"})
        system_player_input(self.world, "UP", Phase.END, True, True)
        self.assertEqual(self.ship.held, {"LEFT"})

    def test_sin_permiso_no_guarda_direccion_pero_si_la_suelta(self):
        self.ship.held = {"UP"}
        system_player_input(self.world, "LEFT", Phase.START, False, False)
        system_player_input(self.world, "UP", Phase.END, False, False)
        self.assertEqual(self.ship.held, set())

    def test_fire_deja_un_disparo_pendiente_solo_si_se_puede_disparar(self):
        system_player_input(self.world, "FIRE", Phase.START, True, False)
        self.assertEqual((self.weapon.held, self.weapon.trigger), (True, False))
        system_player_input(self.world, "FIRE", Phase.END, True, True)
        system_player_input(self.world, "FIRE", Phase.START, True, True)
        self.assertEqual((self.weapon.held, self.weapon.trigger), (True, True))


class DyingWithTheLastBaseTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine.start_game()
        self.state = self.engine.state
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.scene.clock.blast_left = 0
        self.world = self.scene.world

    def kill_player_and_bases(self):
        for base, c_b in self.world.get_component(CBase):
            core = next(e for e, c_p in self.world.get_component(CBasePart)
                        if c_p.base == base and c_p.kind == "core")
            shot = pygame.Vector2(0, -1) if c_b.orientation == "vertical" else pygame.Vector2(1, 0)
            damage_base_part(self.world, core, shot)
        self.world.add_component(self.scene.player, CDestroy())

    def run_until_scene_change(self):
        for _ in range(round(5 / DT)):
            self.scene.do_update(DT)
            if self.engine._next_scene is not None:
                return self.engine._next_scene
        self.fail("el nivel no terminó")

    def test_morir_en_el_frame_en_que_cae_la_ultima_base_cuesta_una_vida(self):
        lives = self.state.lives
        self.kill_player_and_bases()
        self.scene.do_update(DT)
        self.assertIsNone(self.engine._next_scene)  # primero se ve la explosión de la nave
        self.assertEqual(self.run_until_scene_change(), "PLAY")
        self.assertEqual(self.state.lives, lives - 1)
        self.assertEqual(self.state.lives_used, 1)
        self.assertEqual(self.state.level, 2)  # y el nivel queda superado
        self.assertEqual(self.state.bases_destroyed, set())

    def test_si_era_la_ultima_nave_es_derrota_aunque_cayera_la_ultima_base(self):
        self.state.lives = 0
        self.kill_player_and_bases()
        self.assertEqual(self.run_until_scene_change(), "DEFEAT")
        self.assertEqual(self.state.level, 1)

    def test_destruir_la_ultima_base_con_vida_pasa_de_nivel_sin_costo(self):
        lives = self.state.lives
        for base, c_b in self.world.get_component(CBase):
            core = next(e for e, c_p in self.world.get_component(CBasePart)
                        if c_p.base == base and c_p.kind == "core")
            shot = pygame.Vector2(0, -1) if c_b.orientation == "vertical" else pygame.Vector2(1, 0)
            damage_base_part(self.world, core, shot)
        self.assertEqual(self.run_until_scene_change(), "PLAY")
        self.assertEqual((self.state.level, self.state.lives), (2, lives))


if __name__ == "__main__":
    unittest.main()
