import pygame

from src.create.prefab_creator import (create_base_placeholder, create_player,
                                       create_special_shot_message, create_stars,
                                       create_text)
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_weapon import CWeapon
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_camera import system_camera_follow
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_minimap import system_minimap_rendering
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player import HEADING_KEYS, system_player_movement, system_player_sprite
from src.ecs.systems.s_rendering import system_rendering, system_world_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_parallax, system_star_rendering
from src.ecs.systems.s_weapon import system_bullet_cleanup, system_player_fire
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.camera import Camera
from src.engine.data_loader import level_numbers, load_level
from src.engine.difficulty import difficulty_params
from src.engine.hud import Hud
from src.engine.level_flow import after_level_cleared, after_player_died
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class PlayScene(Scene):
    """Escena de nivel: mundo, cámara, estrellas y minimapa (jugador y bases provisionales)."""

    def do_create(self) -> None:
        eng = self.engine
        ServiceLocator.music.stop()
        self.camera = Camera(eng.world_size, eng.viewport)
        level = load_level(eng.level)
        start = level["player_start"]
        self.player_cfg = load_json("assets/cfg/player.json")
        self.player = create_player(self.world, pygame.Vector2(start["x"], start["y"]),
                                    self.player_cfg,
                                    level["special_shot"])
        create_special_shot_message(self.world, self.player_cfg, level["special_shot"],
                                    eng.viewport.centerx)
        for b in level["bases"]:
            create_base_placeholder(self.world, pygame.Vector2(b["x"], b["y"]))
        create_stars(self.world, eng.cfg_world, eng.viewport)
        self.round = level["round"]
        self.difficulty = difficulty_params(level)  # lo consumen spawn, steering y alertas
        self.hud = Hud(ServiceLocator.fonts.get("main"), eng.state.cfg["life_icons_max"])
        self.level_total_bases = len(level["bases"])
        self.camera.follow(pygame.Vector2(start["x"], start["y"]))
        self.camera.delta = pygame.Vector2()
        # Pausa: el mundo queda intacto y solo se congela; no se destruye nada.
        self.paused = False
        self.pause_text = ServiceLocator.fonts.get("main").render(
            "JUEGO PAUSADO", False, pygame.Color(255, 255, 255))
        # BLAST OFF!: al empezar el nivel el jugador no se mueve hasta que acaba la cuenta.
        blast = eng.cfg_world["blast_off"]
        self.blast_left = blast["seconds"]
        self.blast_text = ServiceLocator.fonts.get("main").render(
            blast["text"], False, pygame.Color(255, 255, 255))
        if ServiceLocator.sounds.has("blast_off"):
            ServiceLocator.sounds.play("blast_off")

    def do_action(self, action: str, phase: Phase) -> None:
        if action in HEADING_KEYS:
            # Las teclas de dirección se registran siempre (también en pausa) para que
            # soltar una tecla durante la pausa no deje la nave girando con una tecla fantasma.
            held = self.world.component_for_entity(self.player, CPlayerShip).held
            (held.add if phase == Phase.START else held.discard)(action)
            return
        if action == "FIRE":
            # Como las direcciones, se registra también en pausa para no perder el soltar la tecla.
            weapon = self.world.component_for_entity(self.player, CWeapon)
            weapon.held = phase == Phase.START
            if weapon.held and not self.paused:
                weapon.trigger = True
            return
        if phase != Phase.START:
            return
        if action == "PAUSE":
            self.paused = not self.paused  # P alterna entre jugar y pausar
            return
        if self.paused and action == "SELECT":
            # Acceso al menú del título desde la pausa (#27 lo convertirá en el menú de opciones).
            if action == "SELECT":
                self.engine.switch_scene("TITLE")
            return
        if self.blast_left > 0:
            # Durante BLAST OFF! el jugador no controla la nave (ni guarda la dirección para después).
            return
        dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        if action in dirs:
            self.direction = pygame.Vector2(dirs[action])

    def bases_remaining(self) -> int:
        return sum(1 for _, t in self.world.get_component(CMinimapTrack) if t.kind == "base")

    def level_cleared(self) -> None:
        """Se destruyeron todas las bases: siguiente nivel o victoria."""
        self.engine.switch_scene(after_level_cleared(self.engine.state, level_numbers()))

    def player_died(self) -> None:
        """El jugador murió: pierde una vida y repite el nivel, o va a derrota."""
        self.engine.switch_scene(after_player_died(self.engine.state))

    def do_update(self, delta_time: float) -> None:
        # La pausa va primero: congela también la cuenta de BLAST OFF!.
        if self.paused:
            # En pausa solo las estrellas siguen brillando, quietas (sin parallax ni movimiento).
            system_star_blink(self.world, delta_time)
            return
        if self.blast_left > 0:
            self.blast_left = max(0.0, self.blast_left - delta_time)
            system_star_blink(self.world, delta_time)
            return
        system_lifetime(self.world, delta_time)
        system_player_movement(self.world, delta_time)
        system_player_sprite(self.world)
        system_player_fire(self.world, delta_time)
        system_movement(self.world, delta_time)
        system_wraparound(self.world, self.engine.world_size)
        system_camera_follow(self.world, self.camera)
        system_bullet_cleanup(self.world, self.camera, self.player_cfg["weapon"]["offscreen_margin"])
        if self.level_total_bases and self.bases_remaining() == 0:
            self.level_cleared()
            return
        system_star_blink(self.world, delta_time)
        system_star_parallax(self.world, self.engine.viewport, self.camera.delta,
                             self.engine.cfg_world["stars_parallax_factor"])

    def do_draw(self, screen: pygame.Surface) -> None:
        screen.set_clip(self.engine.viewport)
        system_star_rendering(self.world, screen)
        screen.set_clip(None)
        if self.paused:
            # Desaparecen jugador, bases, interfaz y minimapa; queda el fondo y el aviso.
            screen.blit(self.pause_text, self.pause_text.get_rect(
                center=self.engine.viewport.center))
            return
        system_world_rendering(self.world, screen, self.camera)
        system_rendering(self.world, screen)
        system_minimap_rendering(self.world, screen, self.engine.cfg_world["minimap"],
                                 self.engine.world_size)
        self.hud.draw(screen, self.engine.state, self.round)
        if self.blast_left > 0:
            screen.blit(self.blast_text, self.blast_text.get_rect(
                center=self.engine.viewport.center))
