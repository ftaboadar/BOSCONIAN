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
        # Pausa: el mundo queda intacto y solo se congela; no se destruye nada.
        self.paused = False
        # Salir al título pierde el progreso: antes se pide confirmación (mundo congelado).
        self.confirm_exit = False
        white = pygame.Color(255, 255, 255)
        font = ServiceLocator.fonts.get("main")
        self.confirm_lines = [font.render(t, False, white) for t in eng.cfg_menu["exit_confirm"]]
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
        if phase != Phase.START:
            return
        if self.confirm_exit:
            if action == "SELECT":
                self.engine.switch_scene("TITLE")
            elif action == "BACK":
                self.confirm_exit = False  # ESC otra vez: cancela y vuelve a donde estaba
            return
        if action == "BACK":
            self.confirm_exit = True  # ESC pide confirmar, jugando o en pausa
            return
        if action == "PAUSE":
            self.paused = not self.paused  # P alterna entre jugar y pausar
            return
        if self.paused:
            # Acceso al título desde la pausa (#27 lo convertirá en el menú de opciones).
            if action == "SELECT":
                self.confirm_exit = True
            return
        if self.blast_left > 0:
            # Durante BLAST OFF! el jugador no controla la nave (ni guarda la dirección para después).
            return
        dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        if action in dirs:
            self.direction = pygame.Vector2(dirs[action])

    def do_update(self, delta_time: float) -> None:
        # La pausa va primero: congela también la cuenta de BLAST OFF!.
        if self.paused or self.confirm_exit:
            # En pausa solo las estrellas siguen brillando, quietas (sin parallax ni movimiento).
            system_star_blink(self.world, delta_time)
            return
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
        if self.confirm_exit:
            cx, cy = self.engine.viewport.center
            for i, surf in enumerate(self.confirm_lines):
                screen.blit(surf, surf.get_rect(center=(cx, cy - 32 + i * 14)))
            return
        if self.paused:
            # Desaparecen jugador, bases, interfaz y minimapa; queda el fondo y el aviso.
            screen.blit(self.pause_text, self.pause_text.get_rect(
                center=self.engine.viewport.center))
            return
        system_world_rendering(self.world, screen, self.camera)
        system_rendering(self.world, screen)
        system_minimap_rendering(self.world, screen, self.engine.cfg_world["minimap"],
                                 self.engine.world_size)
        if self.blast_left > 0:
            screen.blit(self.blast_text, self.blast_text.get_rect(
                center=self.engine.viewport.center))
