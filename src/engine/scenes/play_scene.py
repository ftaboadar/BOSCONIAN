import pygame

from src.create.prefab_creator import (create_base, create_enemy_spawner,
                                       create_player_placeholder, create_stars, create_text)
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_camera import system_camera_follow
from src.ecs.systems.s_enemy_spawner import system_enemy_despawn, system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_minimap import system_minimap_rendering
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_rendering import system_rendering, system_world_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_parallax, system_star_rendering
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.camera import Camera
from src.engine.data_loader import load_bases, load_enemies, load_entity_cfg, load_level
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class PlayScene(Scene):
    """Escena de nivel: mundo, cámara, estrellas, minimapa, bases y enemigos (jugador provisional)."""

    def do_create(self) -> None:
        eng = self.engine
        ServiceLocator.music.stop()
        self.camera = Camera(eng.world_size, eng.viewport)
        level = load_level(eng.level)
        # Velocidad del jugador (el hito 3 añade la aceleración); los enemigos van algo más rápido.
        self.player_speed = load_entity_cfg("player", ("max_speed",))["max_speed"]
        start = level["player_start"]
        self.player = create_player_placeholder(self.world, pygame.Vector2(start["x"], start["y"]))
        cfg_bases = load_bases()
        for b in level["bases"]:
            create_base(self.world, pygame.Vector2(b["x"], b["y"]), b["orientation"], cfg_bases)
        # Enemigos I, P y E: salen alrededor del jugador a un ritmo que sube con la dificultad.
        self.cfg_enemies = load_enemies()
        create_enemy_spawner(self.world, self.cfg_enemies, level["difficulty"])
        create_stars(self.world, eng.cfg_world, eng.viewport)
        create_text(self.world, f"ROUND {level['round']}", pygame.Color(255, 255, 255),
                    pygame.Vector2(216, 190))
        self.camera.follow(pygame.Vector2(start["x"], start["y"]))
        self.camera.delta = pygame.Vector2()
        self.direction = pygame.Vector2(0, -1)
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
        if phase != Phase.START:
            return
        if action == "PAUSE":
            self.paused = not self.paused  # P alterna entre jugar y pausar
            return
        if self.paused:
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
        self.world.component_for_entity(self.player, CVelocity).vel = self.direction * self.player_speed
        player_pos = self.world.component_for_entity(self.player, CTransform).pos
        system_enemy_spawner(self.world, player_pos, self.engine.world_size, self.cfg_enemies,
                             self.player_speed, delta_time)
        system_enemy_state(self.world, player_pos, self.engine.world_size, delta_time)
        system_movement(self.world, delta_time)
        system_wraparound(self.world, self.engine.world_size)
        system_enemy_despawn(self.world, player_pos, self.engine.world_size,
                             self.cfg_enemies["spawn"]["despawn_distance"])
        system_camera_follow(self.world, self.camera)
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
        if self.blast_left > 0:
            screen.blit(self.blast_text, self.blast_text.get_rect(
                center=self.engine.viewport.center))
