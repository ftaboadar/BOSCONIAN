"""Pruebas de las bases (#22): seis torretas y núcleo, orientación, puntos y destrucción."""

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

from src.create.prefab_creator import create_base
from src.ecs.components.c_base import CBase
from src.ecs.components.c_base_part import CBasePart
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_points import CPoints
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_base_damage import BASE_DESTROYED, damage_base_part
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine import data_loader
from src.engine.data_loader import ConfigError, load_bases
from src.engine.game_engine import GameEngine

POS = pygame.Vector2(300, 400)


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = GameEngine()  # deja listos la pantalla y el ServiceLocator
        cls.cfg = load_bases()

    @classmethod
    def tearDownClass(cls):
        cls.engine._clean()

    def setUp(self):
        self.world = esper.World()

    def parts(self, base, kind):
        """Entidades de las partes vivas de `base` del tipo dado (turret o core)."""
        return [ent for ent, c_p in self.world.get_component(CBasePart)
                if c_p.base == base and c_p.kind == kind]

    def offsets(self, base, kind):
        return sorted(tuple(self.world.component_for_entity(ent, CTransform).pos - POS)
                      for ent in self.parts(base, kind))


class BaseStructureTests(BaseTestCase):
    def test_tiene_seis_torretas_y_un_nucleo_en_el_centro(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        self.assertEqual(len(self.parts(base, "turret")), 6)
        self.assertEqual(self.offsets(base, "core"), [(0, 0)])
        self.assertEqual(self.world.component_for_entity(base, CTransform).pos, POS)

    def test_base_vale_1500_y_cada_torreta_200_con_la_config_real(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        self.assertEqual(self.world.component_for_entity(base, CPoints).points, 1500)
        turret_points = [self.world.component_for_entity(t, CPoints).points
                         for t in self.parts(base, "turret")]
        self.assertEqual(turret_points, [200] * 6)

    def test_esta_quieta_en_el_mundo_y_se_ve_en_el_minimapa(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        for ent in [base] + self.parts(base, "turret") + self.parts(base, "core"):
            self.assertTrue(self.world.has_component(ent, CWorld))
            self.assertFalse(self.world.has_component(ent, CVelocity))
        self.assertEqual(self.world.component_for_entity(base, CMinimapTrack).kind, "base")
        self.assertEqual(len(self.world.get_component(CMinimapTrack)), 1)

    def test_la_orientacion_gira_la_base_un_cuarto_de_vuelta(self):
        vertical = create_base(self.world, POS, "vertical", self.cfg)
        horizontal = create_base(self.world, POS, "horizontal", self.cfg)
        # Vertical: abierta arriba y abajo (el núcleo se alcanza con un disparo vertical).
        self.assertEqual(self.offsets(vertical, "turret"),
                         [(-28, 0), (-12, -24), (-12, 24), (12, -24), (12, 24), (28, 0)])
        self.assertEqual(self.offsets(horizontal, "turret"),
                         [(-24, -12), (-24, 12), (0, -28), (0, 28), (24, -12), (24, 12)])
        self.assertEqual(self.world.component_for_entity(vertical, CBase).orientation, "vertical")
        self.assertEqual(self.world.component_for_entity(horizontal, CBase).orientation,
                         "horizontal")
        self.assertEqual(self.world.component_for_entity(vertical, CSurface).surf.get_size(),
                         (72, 64))
        self.assertEqual(self.world.component_for_entity(horizontal, CSurface).surf.get_size(),
                         (64, 72))

    def test_el_fondo_magenta_del_sprite_queda_transparente(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        surf = self.world.component_for_entity(base, CSurface).surf
        self.assertEqual(surf.get_at((0, 0)).a, 0)
        magenta = [1 for x in range(surf.get_width()) for y in range(surf.get_height())
                   if surf.get_at((x, y))[:3] == (255, 0, 255) and surf.get_at((x, y)).a]
        self.assertEqual(magenta, [])
        self.assertEqual(surf.get_at((36, 32)).a, 255)  # el núcleo sí se dibuja


UP, DOWN, LEFT, RIGHT = (pygame.Vector2(v) for v in ((0, -1), (0, 1), (-1, 0), (1, 0)))


class BaseDestructionTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.destroyed = []
        # esper guarda los handlers por weakref: hay que conservar la referencia.
        self.on_destroyed = lambda base, pos: self.destroyed.append((base, tuple(pos)))
        esper.set_handler(BASE_DESTROYED, self.on_destroyed)
        self.addCleanup(esper.remove_handler, BASE_DESTROYED, self.on_destroyed)

    def alive(self, base):
        return self.world.entity_exists(base)

    def test_destruir_una_torreta_da_200_y_la_base_sigue(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        turret = self.parts(base, "turret")[0]
        self.assertEqual(damage_base_part(self.world, turret, UP), 200)
        self.assertFalse(self.world.entity_exists(turret))
        self.assertEqual(len(self.parts(base, "turret")), 5)
        self.assertTrue(self.alive(base))
        self.assertEqual(self.destroyed, [])

    def test_la_torreta_destruida_se_ve_distinta(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        other = create_base(self.world, POS, "vertical", self.cfg)
        before = pygame.image.tobytes(self.world.component_for_entity(base, CSurface).surf, "RGBA")
        damage_base_part(self.world, self.parts(base, "turret")[0], UP)
        after = pygame.image.tobytes(self.world.component_for_entity(base, CSurface).surf, "RGBA")
        self.assertNotEqual(before, after)
        # Cada base tiene su propio sprite: la otra queda intacta.
        self.assertEqual(
            pygame.image.tobytes(self.world.component_for_entity(other, CSurface).surf, "RGBA"),
            before)

    def test_se_destruye_al_eliminar_las_seis_torretas(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        points = [damage_base_part(self.world, t, LEFT) for t in self.parts(base, "turret")]
        self.assertEqual(points, [200, 200, 200, 200, 200, 200 + 1500])
        self.assertFalse(self.alive(base))
        self.assertEqual(self.world.get_component(CBasePart), [])
        self.assertEqual(self.world.get_component(CMinimapTrack), [])
        self.assertEqual(self.destroyed, [(base, (300, 400))])

    def test_se_destruye_con_un_unico_disparo_al_nucleo(self):
        for orientation, shots in (("vertical", (UP, DOWN)), ("horizontal", (LEFT, RIGHT))):
            for shot in shots:
                with self.subTest(orientation=orientation, shot=tuple(shot)):
                    self.world = esper.World()
                    self.destroyed.clear()
                    base = create_base(self.world, POS, orientation, self.cfg)
                    core = self.parts(base, "core")[0]
                    self.assertEqual(damage_base_part(self.world, core, shot), 1500)
                    self.assertFalse(self.alive(base))
                    self.assertEqual(self.world.get_component(CBasePart), [])
                    self.assertEqual(self.destroyed, [(base, (300, 400))])

    def test_el_nucleo_solo_es_vulnerable_en_la_direccion_de_la_orientacion(self):
        for orientation, shots in (("vertical", (LEFT, RIGHT)), ("horizontal", (UP, DOWN))):
            for shot in shots:
                with self.subTest(orientation=orientation, shot=tuple(shot)):
                    self.world = esper.World()
                    base = create_base(self.world, POS, orientation, self.cfg)
                    core = self.parts(base, "core")[0]
                    self.assertEqual(damage_base_part(self.world, core, shot), 0)
                    self.assertTrue(self.alive(base))
                    self.assertEqual(len(self.parts(base, "turret")), 6)
                    self.assertEqual(self.destroyed, [])

    def test_una_parte_ya_destruida_no_vuelve_a_dar_puntos(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        turret = self.parts(base, "turret")[0]
        core = self.parts(base, "core")[0]
        damage_base_part(self.world, turret, UP)
        self.assertEqual(damage_base_part(self.world, turret, UP), 0)
        damage_base_part(self.world, core, UP)
        self.assertEqual(damage_base_part(self.world, core, UP), 0)
        self.assertEqual(len(self.destroyed), 1)

    def test_los_restos_se_dibujan_bien_aunque_la_base_cruce_el_borde_del_mundo(self):
        # La torreta dio la vuelta al mundo: su posición ya no está junto a la de la base.
        world_size = pygame.Vector2(1024, 1024)
        images = []
        for pos in (POS, pygame.Vector2(5, 5)):
            base = create_base(self.world, pos, "vertical", self.cfg)
            system_wraparound(self.world, world_size)
            for turret in self.parts(base, "turret"):
                if len(self.parts(base, "turret")) > 1:
                    damage_base_part(self.world, turret, UP)
            images.append(pygame.image.tobytes(
                self.world.component_for_entity(base, CSurface).surf, "RGBA"))
        self.assertEqual(images[0], images[1])

    def test_destruir_una_base_no_toca_a_las_demas(self):
        base = create_base(self.world, POS, "vertical", self.cfg)
        other = create_base(self.world, pygame.Vector2(700, 700), "horizontal", self.cfg)
        damage_base_part(self.world, self.parts(base, "core")[0], UP)
        self.assertTrue(self.alive(other))
        self.assertEqual(len(self.parts(other, "turret")), 6)
        self.assertEqual(len(self.parts(other, "core")), 1)


class BasesConfigTests(unittest.TestCase):
    def load(self, change):
        """Carga una copia de bases.json modificada por `change`."""
        cfg = copy.deepcopy(load_bases())
        change(cfg)
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "bases.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with mock.patch.object(data_loader, "CFG_DIR", tmp):
                return load_bases()

    def test_exige_exactamente_seis_torretas(self):
        with self.assertRaisesRegex(ConfigError, "6 torretas"):
            self.load(lambda cfg: cfg["turret"]["offsets"].pop())

    def test_exige_los_puntos_de_base_y_torreta(self):
        with self.assertRaisesRegex(ConfigError, "points.*turret"):
            self.load(lambda cfg: cfg["points"].pop("turret"))


class PlaySceneBasesTests(unittest.TestCase):
    def test_el_nivel_coloca_sus_bases_con_la_posicion_y_orientacion_del_json(self):
        engine = GameEngine()
        self.addCleanup(engine._clean)
        engine._apply_scene_change("PLAY")
        world = engine._current_scene.world
        bases = sorted((c_t.pos.x, c_t.pos.y, c_b.orientation)
                       for _, (c_t, c_b) in world.get_components(CTransform, CBase))
        # Las tres bases de assets/cfg/levels/level_01.json.
        self.assertEqual(bases, [(300, 400, "horizontal"), (620, 800, "horizontal"),
                                 (760, 300, "vertical")])
        self.assertEqual(sum(c_p.kind == "turret" for _, c_p in world.get_component(CBasePart)), 18)


if __name__ == "__main__":
    unittest.main()
