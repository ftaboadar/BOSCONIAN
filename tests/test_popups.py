"""Pruebas de los carteles de puntos (#89): al destruir algo aparece su puntaje donde ocurrió,
sube un poco y desaparece solo."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import create_score_popup
from src.ecs.components.c_lifetime import CLifetime
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_movement import system_movement
from src.engine.data_loader import load_enemies, load_json
from src.engine.game_engine import GameEngine
from tests.test_combat_cycle import CombatCycleTestCase, DT

POPUP = load_json("assets/cfg/world.json")["score_popup"]
CHAR_WIDTH = 8  # PressStart2P a tamaño 8


def popups(world):
    """Los carteles: entidades que viven un tiempo y se mueven (el aviso del disparo especial no se mueve)."""
    return [e for e, (_l, _v) in world.get_components(CLifetime, CVelocity)]


def popup_width(world, ent):
    return world.component_for_entity(ent, CSurface).surf.get_width()


class PopupPrefabTests(unittest.TestCase):
    def setUp(self):
        GameEngine()
        self.world = esper.World()

    def test_el_cartel_muestra_los_puntos_en_su_posicion(self):
        ent = create_score_popup(self.world, pygame.Vector2(300, 400), 1500, POPUP)
        self.assertEqual(tuple(self.world.component_for_entity(ent, CTransform).pos), (300, 400))
        self.assertEqual(popup_width(self.world, ent), 4 * CHAR_WIDTH)  # "1500"
        ent2 = create_score_popup(self.world, pygame.Vector2(0, 0), 200, POPUP)
        self.assertEqual(popup_width(self.world, ent2), 3 * CHAR_WIDTH)  # "200"

    def test_sube_despacio_y_desaparece_a_su_hora(self):
        ent = create_score_popup(self.world, pygame.Vector2(100, 100), 200, POPUP)
        for _ in range(round(POPUP["seconds"] / 2 / DT)):
            system_lifetime(self.world, DT)
            system_movement(self.world, DT)
        self.assertTrue(self.world.entity_exists(ent))
        y = self.world.component_for_entity(ent, CTransform).pos.y
        self.assertAlmostEqual(y, 100 - POPUP["rise_speed"] * POPUP["seconds"] / 2, delta=1.0)
        for _ in range(round(POPUP["seconds"] / DT)):
            system_lifetime(self.world, DT)
            system_movement(self.world, DT)
        self.assertFalse(self.world.entity_exists(ent))

    def test_el_color_sale_de_la_configuracion(self):
        ent = create_score_popup(self.world, pygame.Vector2(0, 0), 50, {**POPUP, "color": {"r": 10, "g": 200, "b": 30}})
        surf = self.world.component_for_entity(ent, CSurface).surf
        colors = {tuple(surf.get_at((x, y)))[:3] for x in range(surf.get_width()) for y in range(surf.get_height())
                  if surf.get_at((x, y)).a > 0}
        self.assertIn((10, 200, 30), colors)

    def test_la_configuracion_trae_lo_necesario(self):
        for key in ("seconds", "rise_speed", "color"):
            self.assertIn(key, POPUP)
        self.assertGreater(POPUP["seconds"], 0)


class EnemyPopupTests(CombatCycleTestCase):
    with_base = False

    def test_matar_un_enemigo_muestra_sus_puntos_donde_murio(self):
        enemy = self.still_enemy("P", (700, 700))
        self.bullet((700, 700), (0, 0))
        self.step(DT)
        self.assertFalse(self.alive(enemy))
        (pop,) = popups(self.world)
        points = load_enemies()["types"]["P"]["points"]
        self.assertEqual(popup_width(self.world, pop), len(str(points)) * CHAR_WIDTH)
        pos = self.world.component_for_entity(pop, CTransform).pos
        self.assertLess(pos.distance_to(pygame.Vector2(700, 700)), 2 * POPUP["rise_speed"] * DT + 1)

    def test_un_cartel_por_cada_enemigo_con_su_valor(self):
        for kind, x in (("I", 600), ("E", 800)):
            self.still_enemy(kind, (x, 700))
            self.bullet((x, 700), (0, 0))
        self.step(DT)
        widths = sorted(popup_width(self.world, p) for p in popups(self.world))
        self.assertEqual(widths, [2 * CHAR_WIDTH, 2 * CHAR_WIDTH])  # 50 y 70

    def test_el_cartel_desaparece_solo(self):
        self.still_enemy("I", (700, 700))
        self.bullet((700, 700), (0, 0))
        self.step(DT)
        self.assertEqual(len(popups(self.world)), 1)
        self.step(POPUP["seconds"] + 0.2)
        self.assertEqual(popups(self.world), [])

    def test_si_no_se_gana_nada_no_hay_cartel(self):
        self.bullet((900, 900), (0, 0))
        self.step(0.3)
        self.assertEqual(popups(self.world), [])

    def test_chocar_con_un_enemigo_no_da_puntos_ni_cartel(self):
        self.still_enemy("I", (512, 512))
        self.step(DT)
        self.assertEqual(popups(self.world), [])

    def test_se_dibuja_sin_fallar(self):
        self.still_enemy("I", (700, 700))
        self.bullet((700, 700), (0, 0))
        self.step(DT)
        self.scene.do_draw(pygame.Surface((256, 208)))


class BasePopupTests(CombatCycleTestCase):
    def widths(self):
        return sorted(popup_width(self.world, p) // CHAR_WIDTH for p in popups(self.world))

    def hit_turret(self, _n=0):
        """Dispara a la primera torreta que queda (la lista se achica al caer cada una)."""
        turret = self.parts("turret")[0]
        self.bullet(self.world.component_for_entity(turret, CTransform).pos, (0, 0))
        self.step(DT)

    def test_una_torreta_muestra_200(self):
        self.hit_turret(0)
        self.assertEqual(self.widths(), [3])

    def test_la_sexta_torreta_muestra_dos_carteles_separados_200_y_1500(self):
        for i in range(5):
            self.hit_turret(i)
        before = len(popups(self.world))
        self.hit_turret(5)
        new = popups(self.world)[before:]
        self.assertEqual(sorted(popup_width(self.world, p) // CHAR_WIDTH for p in new), [3, 4])  # "200" y "1500"
        poss = [self.world.component_for_entity(p, CTransform).pos for p in new]
        self.assertGreater(poss[0].distance_to(poss[1]), 1)  # no se encimen

    def test_un_disparo_al_nucleo_muestra_solo_1500(self):
        core = self.parts("core")[0]
        pos = self.world.component_for_entity(core, CTransform).pos
        self.bullet(pos + pygame.Vector2(0, 10), (0, -220))
        self.step(0.2)
        self.assertEqual(self.widths(), [4])

    def test_un_disparo_que_no_hace_dano_no_muestra_cartel(self):
        core = self.parts("core")[0]
        pos = self.world.component_for_entity(core, CTransform).pos
        self.bullet(pos, (220, 0))  # perpendicular: el núcleo no recibe daño
        self.step(DT)
        self.assertEqual(popups(self.world), [])

    def test_los_puntos_del_marcador_no_cambian_por_los_carteles(self):
        for i in range(6):
            self.hit_turret(i)
        self.assertEqual(self.state.score, 6 * 200 + 1500)


class WithoutConfigTests(unittest.TestCase):
    def test_sin_popup_cfg_el_sistema_no_crea_carteles_como_antes(self):
        from src.create.prefab_creator import create_enemy, create_player_bullet
        from src.ecs.systems.s_collision import system_collision
        from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
        GameEngine()
        world = esper.World()
        rules = load_rules(load_json("assets/cfg/collisions.json"))
        create_enemy(world, "I", pygame.Vector2(50, 50), pygame.Vector2(0, -1), load_enemies(), 80, 0.0)
        create_player_bullet(world, pygame.Vector2(50, 50), pygame.Vector2(), pygame.Surface((4, 4)))
        points = system_collision_rules(world, system_collision(world), rules)
        self.assertEqual(points, load_enemies()["types"]["I"]["points"])
        self.assertEqual(popups(world), [])


if __name__ == "__main__":
    unittest.main()
