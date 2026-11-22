"""Pruebas de la segunda habilidad especial: escudo (X), ítem del mundo, minimapa y límites."""

import os
import random
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from src.create.prefab_creator import create_ability_item, create_hitbox
from src.ecs.components.c_ability import CAbility, CAbilityItem, CItemSpawner, CShield, CShieldAura
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.components.c_world import CWorld
from src.ecs.systems.s_ability import system_ability_item_spawner
from src.engine.camera import wrap_delta
from src.engine.data_loader import ConfigError, level_numbers, load_ability, load_json, load_level, validate_level
from src.engine.game_engine import GameEngine
from src.engine.input.command import CommandMap, Phase

CFG = load_ability()
DT = 1 / 60


class AbilityConfigTests(unittest.TestCase):
    def test_x_esta_mapeada_a_la_accion_special(self):
        keyboard = load_json("assets/cfg/input.json")["keyboard"]
        self.assertEqual(keyboard["SPECIAL"], "K_x")
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x)
        self.assertEqual(CommandMap(keyboard).translate(event), ("SPECIAL", Phase.START))

    def test_la_habilidad_tiene_limite_y_duracion_en_configuracion(self):
        self.assertGreater(CFG["shield"]["duration"], 0)
        self.assertGreaterEqual(CFG["shield"]["max_charges"], 1)

    def test_cada_nivel_define_su_probabilidad(self):
        chances = [load_level(n)["ability_item_chance"] for n in level_numbers()]
        self.assertEqual(len(chances), 10)
        self.assertTrue(all(0 <= c <= 1 for c in chances))
        self.assertGreater(len(set(chances)), 1)  # varía por nivel

    def test_probabilidad_invalida_se_rechaza(self):
        base = load_level(1)
        for bad in (1.5, -0.1, "alta", True):
            with self.assertRaises(ConfigError):
                validate_level({**base, "ability_item_chance": bad}, "x")

    def test_el_item_se_ve_en_el_minimapa(self):
        minimap = load_json("assets/cfg/world.json")["minimap"]
        self.assertIn("item", minimap["dot_colors"])
        self.assertIn("item", minimap["dot_sizes"])


class ItemSpawnerTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.world = self.scene.world
        self.size = self.engine.world_size

    def tearDown(self):
        self.engine._clean()

    def items(self):
        return self.world.get_component(CAbilityItem)

    def tick(self, chance, rng=None):
        for _, sp in self.world.get_component(CItemSpawner):
            sp.chance = chance
            sp.timer = sp.interval
        system_ability_item_spawner(self.world, pygame.Vector2(512, 512), self.size, CFG["item"], DT,
                                    rng or random.Random(1))

    def test_probabilidad_uno_crea_item_cerca_con_minimapa_y_hitbox(self):
        self.tick(1.0)
        (ent, _), = self.items()
        pos = self.world.component_for_entity(ent, CTransform).pos
        dist = wrap_delta(pos - pygame.Vector2(512, 512), self.size).length()
        self.assertGreaterEqual(dist, CFG["item"]["min_distance"] - 0.01)
        self.assertLessEqual(dist, CFG["item"]["max_distance"] + 0.01)
        self.assertEqual(self.world.component_for_entity(ent, CMinimapTrack).kind, "item")
        self.assertTrue(self.world.has_component(ent, CWorld))
        self.assertEqual(self.world.component_for_entity(ent, type(create_hitbox("ability_item"))).layer, "PICKUP")

    def test_probabilidad_cero_no_crea(self):
        self.tick(0.0)
        self.assertEqual(self.items(), [])

    def test_solo_un_item_a_la_vez(self):
        self.tick(1.0)
        self.tick(1.0)
        self.assertEqual(len(self.items()), 1)

    def test_no_sale_si_el_jugador_tiene_el_maximo(self):
        c_a = self.world.component_for_entity(self.scene.player, CAbility)
        c_a.charges = c_a.max_charges
        self.tick(1.0)
        self.assertEqual(self.items(), [])

    def test_el_item_caduca(self):
        self.scene.clock.blast_left = 0
        self.tick(1.0)
        for _, sp in self.world.get_component(CItemSpawner):
            sp.chance = 0.0  # que no aparezca otro mientras pasa el tiempo
        for _ in range(int(CFG["item"]["lifetime_seconds"] / 0.5) + 2):
            self.scene.do_update(0.5)
        self.assertEqual(self.items(), [])


class ShieldSceneTests(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()
        self.engine._apply_scene_change("PLAY")
        self.scene = self.engine._current_scene
        self.world = self.scene.world
        self.scene.clock.blast_left = 0
        self.player = self.scene.player
        self.ability = self.world.component_for_entity(self.player, CAbility)
        self.pos = self.world.component_for_entity(self.player, CTransform).pos

    def tearDown(self):
        self.engine._clean()

    def press_x(self):
        self.scene.do_action("SPECIAL", Phase.START)
        self.scene.do_update(DT)

    def put_item_on_player(self):
        return create_ability_item(self.world, pygame.Vector2(self.pos), CFG["item"])

    def put_enemy_on_player(self):
        return self.world.create_entity(CTransform(pygame.Vector2(self.pos)), CVelocity(pygame.Vector2()),
                                        create_hitbox("enemy"), CWorld())

    def test_empieza_sin_usos_y_x_no_hace_nada(self):
        self.assertEqual(self.ability.charges, CFG["shield"]["start_charges"])
        self.ability.charges = 0
        self.press_x()
        self.assertFalse(self.world.has_component(self.player, CShield))

    def test_recoger_el_item_da_un_uso_y_lo_retira(self):
        item = self.put_item_on_player()
        self.scene.do_update(DT)
        self.assertEqual(self.ability.charges, 1)
        self.assertFalse(self.world.entity_exists(item))

    def test_con_el_maximo_el_item_se_queda(self):
        self.ability.charges = self.ability.max_charges
        item = self.put_item_on_player()
        self.scene.do_update(DT)
        self.assertEqual(self.ability.charges, self.ability.max_charges)
        self.assertTrue(self.world.entity_exists(item))
        self.assertFalse(self.world.has_component(item, CDestroy))

    def test_x_gasta_un_uso_y_activa_escudo_con_anillo(self):
        self.ability.charges = 2
        self.press_x()
        self.assertEqual(self.ability.charges, 1)
        self.assertTrue(self.world.has_component(self.player, CShield))
        self.assertEqual(len(self.world.get_component(CShieldAura)), 1)

    def test_con_el_escudo_activo_x_no_gasta_otro_uso(self):
        self.ability.charges = 2
        self.press_x()
        self.press_x()
        self.assertEqual(self.ability.charges, 1)

    def test_el_escudo_dura_lo_configurado_y_luego_se_apaga(self):
        self.ability.charges = 1
        self.press_x()
        for _ in range(int((CFG["shield"]["duration"] - 0.5) / 0.1)):
            self.scene.do_update(0.1)
        self.assertTrue(self.world.has_component(self.player, CShield))
        for _ in range(10):
            self.scene.do_update(0.1)
        self.assertFalse(self.world.has_component(self.player, CShield))
        self.assertEqual(self.world.get_component(CShieldAura), [])

    def test_con_escudo_el_choque_no_destruye_nada_y_sin_el_si(self):
        enemy = self.put_enemy_on_player()
        self.ability.charges = 1
        self.press_x()
        self.assertTrue(self.world.entity_exists(self.player))
        self.assertTrue(self.world.entity_exists(enemy))  # no es un arma: tampoco mata al enemigo
        self.assertFalse(self.world.has_component(enemy, CDestroy))

    def test_sin_escudo_el_mismo_choque_si_destruye(self):
        enemy = self.put_enemy_on_player()
        self.scene.do_update(DT)
        self.assertFalse(self.world.entity_exists(enemy) and not self.world.has_component(enemy, CDestroy)
                         and self.world.entity_exists(self.player))

    def test_en_pausa_x_se_ignora(self):
        self.ability.charges = 1
        self.scene.paused = True
        self.scene.do_action("SPECIAL", Phase.START)
        self.scene.paused = False
        self.scene.do_update(DT)
        self.assertEqual(self.ability.charges, 1)
        self.assertFalse(self.world.has_component(self.player, CShield))

    def test_el_anillo_sigue_a_la_nave(self):
        self.ability.charges = 1
        self.press_x()
        for _ in range(5):
            self.scene.do_update(DT)
        (_, (aura_t, _a)), = self.world.get_components(CTransform, CShieldAura)
        self.assertLess((aura_t.pos - self.world.component_for_entity(self.player, CTransform).pos).length(), 0.01)


if __name__ == "__main__":
    unittest.main()
