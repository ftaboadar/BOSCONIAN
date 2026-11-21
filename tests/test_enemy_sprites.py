"""Pruebas de los sprites de los enemigos I, P y E (#85): se dibujan con su nave de naves.png,
miran hacia donde se mueven y su sprite sale de enemies.json."""

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

from src.create.prefab_creator import angle_sprites, create_enemy
from src.ecs.components.c_hitbox import CHitBox
from src.ecs.components.c_angle_sprites import CAngleSprites
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_enemy_sprite import heading_index, system_enemy_sprite
from src.engine import data_loader
from src.engine.data_loader import ConfigError, load_enemies, load_json
from src.engine.game_engine import GameEngine

CFG = load_enemies()
UP, RIGHT, DOWN, LEFT = (pygame.Vector2(v) for v in ((0, -1), (1, 0), (0, 1), (-1, 0)))


class SpriteTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = GameEngine()  # inicia pygame y las imágenes
        self.world = esper.World()

    def enemy(self, kind, direction=UP, pos=(100, 100)):
        return create_enemy(self.world, kind, pygame.Vector2(pos), pygame.Vector2(direction),
                            CFG, 80, 0.0)

    def surf(self, ent):
        return self.world.component_for_entity(ent, CSurface).surf


class HeadingIndexTests(unittest.TestCase):
    """16 pasos de 22,5 grados, en sentido horario desde arriba (índice 0)."""

    def test_los_ocho_rumbos_principales_caen_en_los_indices_pares(self):
        cases = {(0, -1): 0, (1, -1): 2, (1, 0): 4, (1, 1): 6, (0, 1): 8, (-1, 1): 10, (-1, 0): 12, (-1, -1): 14}
        for vel, index in cases.items():
            self.assertEqual(heading_index(pygame.Vector2(vel), 16), index, vel)

    def test_las_direcciones_intermedias_usan_los_indices_impares(self):
        for angle in (22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5):
            vel = pygame.Vector2(0, -1).rotate(angle)  # rotate es horario en pantalla (y hacia abajo)
            self.assertEqual(heading_index(vel, 16) % 2, 1, angle)

    def test_redondea_al_paso_mas_cercano(self):
        self.assertEqual(heading_index(pygame.Vector2(0, -1).rotate(10), 16), 0)   # 10 < 11,25
        self.assertEqual(heading_index(pygame.Vector2(0, -1).rotate(13), 16), 1)   # 13 > 11,25
        self.assertEqual(heading_index(pygame.Vector2(0, -1).rotate(-13), 16), 15)

    def test_da_la_vuelta_completa_sin_salirse_de_rango(self):
        seen = {heading_index(pygame.Vector2(0, -1).rotate(a), 16) for a in range(0, 360, 5)}
        self.assertEqual(seen, set(range(16)))

    def test_velocidad_nula_mira_hacia_arriba(self):
        self.assertEqual(heading_index(pygame.Vector2(), 16), 0)

    def test_funciona_con_otro_numero_de_pasos(self):
        self.assertEqual(heading_index(pygame.Vector2(1, 0), 8), 2)
        self.assertEqual(heading_index(pygame.Vector2(1, 0), 4), 1)


class EnemySpriteTests(SpriteTestCase):
    def test_cada_tipo_usa_el_sprite_de_su_configuracion(self):
        for kind, type_cfg in CFG["types"].items():
            r = type_cfg["sprite"]
            ent = self.enemy(kind, UP)
            self.assertEqual(self.surf(ent).get_size(), (r["w"], r["h"]), kind)

    def test_los_tres_tipos_se_ven_distintos(self):
        looks = {kind: pygame.image.tobytes(self.surf(self.enemy(kind)), "RGBA") for kind in "IPE"}
        self.assertEqual(len(set(looks.values())), 3)

    def test_ya_no_es_un_cuadro_de_un_solo_color(self):
        for kind in "IPE":
            surf = self.surf(self.enemy(kind))
            colors = {tuple(surf.get_at((x, y))) for x in range(surf.get_width())
                      for y in range(surf.get_height())}
            self.assertGreater(len(colors), 2, kind)

    def test_el_sprite_tiene_transparencia(self):
        for kind in "IPE":
            surf = self.surf(self.enemy(kind))
            self.assertTrue(any(surf.get_at((x, y)).a == 0 for x in range(surf.get_width())
                                for y in range(surf.get_height())), kind)

    def test_nace_mirando_hacia_donde_va(self):
        ent = self.enemy("E", RIGHT)
        r = CFG["types"]["E"]["sprite"]
        self.assertEqual(self.surf(ent).get_size(), (r["h"], r["w"]))  # girado 90: ancho y alto cambian

    def test_tiene_las_dieciseis_variantes_como_el_original(self):
        self.assertEqual(CFG["heading_steps"], 16)
        sprites = self.world.component_for_entity(self.enemy("I"), CAngleSprites).surfaces
        self.assertEqual(len(sprites), 16)
        self.assertEqual(len({pygame.image.tobytes(s, "RGBA") for s in sprites}), 16)  # todas distintas

    def test_el_sprite_nacido_es_el_de_su_angulo_intermedio(self):
        ent = self.enemy("I", pygame.Vector2(0, -1).rotate(22.5))  # entre arriba y la diagonal
        sprites = self.world.component_for_entity(ent, CAngleSprites).surfaces
        self.assertIs(self.surf(ent), sprites[1])

    def test_la_hitbox_acompana_al_tamano_de_los_sprites(self):
        hitbox = self.world.component_for_entity(self.enemy("I"), CHitBox).size
        sides = [s for t in CFG["types"].values() for s in (t["sprite"]["w"], t["sprite"]["h"])]
        self.assertGreaterEqual(hitbox.x, min(sides))
        self.assertLessEqual(hitbox.x, max(sides))

    def test_angle_sprites_gira_el_original_en_pasos_iguales(self):
        base = pygame.Surface((4, 10), pygame.SRCALPHA)
        sprites = angle_sprites(base, 16)
        self.assertEqual(len(sprites), 16)
        self.assertEqual(sprites[0].get_size(), (4, 10))     # arriba
        self.assertEqual(sprites[4].get_size(), (10, 4))     # derecha
        self.assertEqual(sprites[8].get_size(), (4, 10))     # abajo
        self.assertEqual(sprites[12].get_size(), (10, 4))    # izquierda
        self.assertGreater(sprites[2].get_width(), 4)        # la diagonal es más ancha que el original
        self.assertEqual(len(angle_sprites(base, 8)), 8)


class SystemEnemySpriteTests(SpriteTestCase):
    def turn(self, ent, direction):
        self.world.component_for_entity(ent, CVelocity).vel = pygame.Vector2(direction) * 80
        system_enemy_sprite(self.world)

    def test_cambia_de_sprite_al_cambiar_de_direccion(self):
        ent = self.enemy("I", UP)
        up = self.surf(ent)
        self.turn(ent, RIGHT)
        self.assertIs(self.surf(ent), self.world.component_for_entity(ent, CAngleSprites).surfaces[4])
        self.assertIsNot(self.surf(ent), up)
        self.turn(ent, DOWN)
        self.assertEqual(self.surf(ent).get_size(), up.get_size())  # abajo: mismo tamaño que arriba

    def test_un_enemigo_detenido_conserva_su_sprite(self):
        ent = self.enemy("P", LEFT)
        turned = self.surf(ent)
        self.world.component_for_entity(ent, CVelocity).vel = pygame.Vector2()
        system_enemy_sprite(self.world)
        self.assertIs(self.surf(ent), turned)

    def test_no_toca_a_las_entidades_que_no_son_enemigos(self):
        other = self.world.create_entity(CSurface(pygame.Surface((3, 3))), CVelocity(pygame.Vector2(5, 0)),
                                         CAngleSprites([pygame.Surface((9, 9)) for _ in range(16)]))
        system_enemy_sprite(self.world)
        self.assertEqual(self.surf(other).get_size(), (3, 3))

    def test_cada_enemigo_sigue_su_propio_rumbo(self):
        a, b = self.enemy("E", UP), self.enemy("E", UP)  # el E mide 7x16: girado cambia de tamaño
        self.turn(a, RIGHT)
        self.assertNotEqual(self.surf(a).get_size(), self.surf(b).get_size())


class EnemyConfigTests(unittest.TestCase):
    def load_with(self, mutate):
        cfg = copy.deepcopy(load_json("assets/cfg/enemies.json"))
        mutate(cfg)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "enemies.json"), "w", encoding="utf-8") as f:
                json.dump(cfg, f)
            with mock.patch.object(data_loader, "CFG_DIR", d):
                return data_loader.load_enemies()

    def test_un_tipo_sin_sprite_falla(self):
        with self.assertRaises(ConfigError):
            self.load_with(lambda c: c["types"]["I"].pop("sprite"))

    def test_heading_steps_es_obligatorio_y_al_menos_ocho(self):
        with self.assertRaises(ConfigError):
            self.load_with(lambda c: c.pop("heading_steps"))
        with self.assertRaises(ConfigError):
            self.load_with(lambda c: c.update(heading_steps=4))
        with self.assertRaises(ConfigError):
            self.load_with(lambda c: c.update(heading_steps="16"))
        self.assertEqual(self.load_with(lambda c: c.update(heading_steps=8))["heading_steps"], 8)

    def test_un_sprite_incompleto_falla(self):
        with self.assertRaises(ConfigError):
            self.load_with(lambda c: c["types"]["E"]["sprite"].pop("w"))

    def test_los_rectangulos_del_proyecto_caen_dentro_de_la_hoja_y_no_estan_vacios(self):
        GameEngine()
        sheet = pygame.image.load("assets/img/naves.png").convert_alpha()
        for kind, t in CFG["types"].items():
            r = pygame.Rect(t["sprite"]["x"], t["sprite"]["y"], t["sprite"]["w"], t["sprite"]["h"])
            self.assertTrue(sheet.get_rect().contains(r), kind)
            self.assertTrue(any(sheet.get_at((x, y)).a > 0 for x in range(r.left, r.right)
                                for y in range(r.top, r.bottom)), kind)


class InGameTests(SpriteTestCase):
    def test_en_el_nivel_cada_enemigo_muestra_el_sprite_de_su_direccion(self):
        """Invariante que no depende del azar: con los enemigos que salgan, en cada fotograma el
        sprite mostrado es el de la dirección en que se mueven, y se dibujan sin fallar."""
        from src.ecs.components.c_enemy_spawner import CEnemySpawner
        from src.ecs.components.c_enemy_state import CEnemyState
        from src.ecs.components.c_invulnerable import CInvulnerable
        self.engine._apply_scene_change("PLAY")
        scene = self.engine._current_scene
        scene.clock.blast_left = 0
        scene.world.add_component(scene.player, CInvulnerable())
        for _, c_sp in scene.world.get_component(CEnemySpawner):
            c_sp.interval = 0.5
        screen = pygame.Surface((256, 208))
        checked = 0
        for i in range(600):
            scene.do_update(1 / 60)
            if i % 30 == 0:
                scene.do_draw(screen)
            for ent, _ in scene.world.get_component(CEnemyState):
                vel = scene.world.component_for_entity(ent, CVelocity).vel
                if vel.length_squared() == 0:
                    continue
                sprites = scene.world.component_for_entity(ent, CAngleSprites).surfaces
                self.assertIs(scene.world.component_for_entity(ent, CSurface).surf,
                              sprites[heading_index(vel, len(sprites))])
                checked += 1
        self.assertGreater(checked, 0, "no salió ningún enemigo en 10 s")


if __name__ == "__main__":
    unittest.main()
