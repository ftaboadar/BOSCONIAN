import pygame

from src.create.prefab_creator import (create_base_placeholder, create_player_placeholder,
                                       create_stars, create_text)
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_camera import system_camera_follow
from src.ecs.systems.s_minimap import system_minimap_rendering
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_rendering import system_rendering, system_world_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_parallax, system_star_rendering
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.camera import Camera
from src.engine.data_loader import load_level
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator

PLACEHOLDER_SPEED = 80  # provisional: el hito 3 lo reemplaza por aceleración


class PlayScene(Scene):
    """Escena de nivel: mundo, cámara, estrellas y minimapa (jugador y bases provisionales)."""

    def do_create(self) -> None:
        eng = self.engine
        ServiceLocator.music.stop()
        self.camera = Camera(eng.world_size, eng.viewport)
        level = load_level(eng.level)
        start = level["player_start"]
        self.player = create_player_placeholder(self.world, pygame.Vector2(start["x"], start["y"]))
        for b in level["bases"]:
            create_base_placeholder(self.world, pygame.Vector2(b["x"], b["y"]))
        create_stars(self.world, eng.cfg_world, eng.viewport)
        create_text(self.world, f"ROUND {level['round']}", pygame.Color(255, 255, 255),
                    pygame.Vector2(216, 190))
        self.camera.follow(pygame.Vector2(start["x"], start["y"]))
        self.camera.delta = pygame.Vector2()
        self.direction = pygame.Vector2(0, -1)
        # BLAST OFF!: al empezar el nivel el jugador no se mueve hasta que acaba la cuenta.
        blast = eng.cfg_world["blast_off"]
        self.blast_left = blast["seconds"]
        self.blast_text = ServiceLocator.fonts.get("main").render(
            blast["text"], False, pygame.Color(255, 255, 255))
        if ServiceLocator.sounds.has("blast_off"):
            ServiceLocator.sounds.play("blast_off")

    def do_action(self, action: str, phase: Phase) -> None:
        if phase != Phase.START:
            return
        dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        if action in dirs:
            self.direction = pygame.Vector2(dirs[action])
        elif action == "PAUSE":
            self.engine.switch_scene("TITLE")

    def do_update(self, delta_time: float) -> None:
        if self.blast_left > 0:
            self.blast_left = max(0.0, self.blast_left - delta_time)
            system_star_blink(self.world, delta_time)
            return
        self.world.component_for_entity(self.player, CVelocity).vel = self.direction * PLACEHOLDER_SPEED
        system_movement(self.world, delta_time)
        system_wraparound(self.world, self.engine.world_size)
        system_camera_follow(self.world, self.camera)
        system_star_blink(self.world, delta_time)
        system_star_parallax(self.world, self.engine.viewport, self.camera.delta,
                             self.engine.cfg_world["stars_parallax_factor"])

    def do_draw(self, screen: pygame.Surface) -> None:
        screen.set_clip(self.engine.viewport)
        system_star_rendering(self.world, screen)
        screen.set_clip(None)
        system_world_rendering(self.world, screen, self.camera)
        system_rendering(self.world, screen)
        system_minimap_rendering(self.world, screen, self.engine.cfg_world["minimap"],
                                 self.engine.world_size)
        if self.blast_left > 0:
            screen.blit(self.blast_text, self.blast_text.get_rect(
                center=self.engine.viewport.center))
