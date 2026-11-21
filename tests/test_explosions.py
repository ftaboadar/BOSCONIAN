"""Pruebas de las explosiones y la muerte del jugador (#17)."""

import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import esper
import pygame

from src.create.prefab_creator import create_explosion
from src.ecs.components.c_animation import CAnimation
from src.ecs.components.c_destroy import CDestroy
from src.ecs.components.c_explosive import CExplosive
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_surface import CSurface
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_explode import system_explode
from src.engine.data_loader import load_json
from src.engine.game_engine import GameEngine

ENGINE = GameEngine()  # inicializa pygame, la ventana y los servicios
CFG = load_json("assets/cfg/explosions.json")


def explosions(world):
    return [ent for ent, _ in world.get_component(CAnimation)]


class AnimationTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()
        self.sheet = pygame.Surface((48, 16))
        self.frames = [pygame.Rect(16 * i, 0, 16, 16) for i in range(3)]

    def make(self, loop):
        return self.w.create_entity(CSurface(self.sheet.subsurface(self.frames[0])),
                                    CAnimation(self.sheet, self.frames, 10, loop))

    def test_avanza_un_frame_por_cada_frame_time(self):
        e = self.make(loop=False)
        system_animation(self.w, 0.05)
        self.assertEqual(self.w.component_for_entity(e, CAnimation).curr_frame, 0)
        system_animation(self.w, 0.05)
        self.assertEqual(self.w.component_for_entity(e, CAnimation).curr_frame, 1)

    def test_sin_loop_se_marca_para_borrar_al_terminar(self):
        e = self.make(loop=False)
        for _ in range(2):
            system_animation(self.w, 0.1)
        self.assertIsNone(self.w.try_component(e, CDestroy))
        system_animation(self.w, 0.1)
        self.assertIsNotNone(self.w.try_component(e, CDestroy))

    def test_con_loop_vuelve_al_inicio(self):
        e = self.make(loop=True)
        for _ in range(3):
            system_animation(self.w, 0.1)
        self.assertEqual(self.w.component_for_entity(e, CAnimation).curr_frame, 0)
        self.assertIsNone(self.w.try_component(e, CDestroy))


class ExplosionTests(unittest.TestCase):
    def setUp(self):
        self.w = esper.World()

    def test_prefab_copia_posicion_y_velocidad(self):
        pos, vel = pygame.Vector2(10, 20), pygame.Vector2(30, 0)
        e = create_explosion(self.w, pos, vel, CFG["simple"])
        pos.x, vel.x = 0, 999
        self.assertEqual(self.w.component_for_entity(e, CTransform).pos, pygame.Vector2(10, 20))
        self.assertEqual(self.w.component_for_entity(e, CVelocity).vel, pygame.Vector2(30, 0))
        self.assertEqual(self.w.component_for_entity(e, CSurface).surf.get_size(), (16, 16))

    def test_explosion_termina_y_se_borra(self):
        e = create_explosion(self.w, pygame.Vector2(), pygame.Vector2(), CFG["simple"])
        for _ in range(len(CFG["simple"]["frames"]) * 10):
            system_animation(self.w, 1 / CFG["simple"]["framerate"])
            system_destroy(self.w)
        self.assertFalse(self.w.entity_exists(e))

    def test_enemigo_deja_una_explosion_con_su_velocidad(self):
        self.w.create_entity(CTransform(pygame.Vector2(100, 100)),
                             CVelocity(pygame.Vector2(40, -10)), CExplosive("simple"), CDestroy())
        system_explode(self.w, CFG)
        system_destroy(self.w)
        exps = explosions(self.w)
        self.assertEqual(len(exps), 1)
        self.assertEqual(self.w.component_for_entity(exps[0], CVelocity).vel,
                         pygame.Vector2(40, -10))

    def test_jugador_deja_varias_explosiones_en_su_radio(self):
        cfg = CFG["player"]
        center = pygame.Vector2(300, 300)
        self.w.create_entity(CTransform(pygame.Vector2(center)),
                             CVelocity(pygame.Vector2(80, 0)), CExplosive("player"), CDestroy())
        system_explode(self.w, CFG)
        exps = explosions(self.w)
        self.assertEqual(len(exps), cfg["count"])
        for e in exps:
            self.assertLessEqual(self.w.component_for_entity(e, CTransform).pos.distance_to(center),
                                 cfg["radius"] + 1e-6)
            if not cfg["keep_velocity"]:
                self.assertEqual(self.w.component_for_entity(e, CVelocity).vel, pygame.Vector2())

    def test_sin_cexplosive_no_hay_explosion(self):
        self.w.create_entity(CTransform(pygame.Vector2()), CDestroy())
        system_explode(self.w, CFG)
        self.assertEqual(explosions(self.w), [])

    def test_sin_cdestroy_no_explota(self):
        self.w.create_entity(CTransform(pygame.Vector2()), CExplosive("simple"))
        system_explode(self.w, CFG)
        self.assertEqual(explosions(self.w), [])


class PlayerDeathTests(unittest.TestCase):
    def setUp(self):
        ENGINE.state.lives = 3
        ENGINE._next_scene = None
        ENGINE._apply_scene_change("PLAY")
        self.scene = ENGINE._current_scene
        self.scene.blast_left = 0

    def run_until_scene_change(self, max_frames=600):
        for frame in range(1, max_frames):
            self.scene.do_update(1 / 60)
            if ENGINE._next_scene is not None:
                return frame
        return None

    def test_muerte_explota_espera_y_descuenta_vida(self):
        self.scene.world.add_component(self.scene.player, CDestroy())
        self.scene.do_update(1 / 60)
        self.assertFalse(self.scene.world.entity_exists(self.scene.player))
        self.assertEqual(len(explosions(self.scene.world)), CFG["player"]["count"])
        frames = self.run_until_scene_change()
        self.assertIsNotNone(frames)
        self.assertAlmostEqual((frames + 1) / 60, CFG["player"]["death_wait"], delta=2 / 60)
        self.assertEqual(ENGINE._next_scene, "PLAY")
        self.assertEqual(ENGINE.state.lives, 2)

    def test_jugador_muere_al_chocar_con_una_base(self):
        base_pos = next(c_t.pos for _, (c_t, c_m) in
                        self.scene.world.get_components(CTransform, CMinimapTrack)
                        if c_m.kind == "base")
        self.scene.world.component_for_entity(self.scene.player, CTransform).pos = \
            pygame.Vector2(base_pos)
        self.scene.do_update(1 / 60)
        self.assertFalse(self.scene.world.entity_exists(self.scene.player))

    def test_la_pausa_congela_la_espera(self):
        self.scene.world.add_component(self.scene.player, CDestroy())
        self.scene.do_update(1 / 60)
        self.scene.paused = True
        for _ in range(600):
            self.scene.do_update(1 / 60)
        self.assertIsNone(ENGINE._next_scene)

    def test_camara_quieta_sin_jugador(self):
        self.scene.world.add_component(self.scene.player, CDestroy())
        self.scene.do_update(1 / 60)
        self.assertEqual(self.scene.camera.delta, pygame.Vector2())


if __name__ == "__main__":
    unittest.main()
