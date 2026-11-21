import pygame

from src.create.prefab_creator import (create_base, create_enemy_spawner,
                                       create_player_placeholder, create_stars)
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.ecs.components.c_velocity import CVelocity
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_base_behavior import system_base_cores, system_turrets
from src.ecs.systems.s_camera import system_camera_follow
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_enemy_bullet import system_enemy_bullets
from src.ecs.systems.s_enemy_spawner import system_enemy_despawn, system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_explode import system_explode
from src.ecs.systems.s_minimap import system_minimap_rendering
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_rendering import system_rendering, system_world_rendering
from src.ecs.systems.s_star import system_star_blink, system_star_parallax, system_star_rendering
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.camera import Camera
from src.engine.data_loader import (level_numbers, load_bases, load_enemies, load_entity_cfg,
                                    load_json, load_level)
from src.engine.difficulty import difficulty_factor, difficulty_params
from src.engine.hud import Hud
from src.engine.level_flow import after_level_cleared, after_player_died
from src.engine.input.command import Phase
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator


class PlayScene(Scene):
    """Escena de nivel: mundo, cámara, estrellas, minimapa, bases y enemigos (jugador provisional)."""

    def do_create(self) -> None:
        eng = self.engine
        self.collision_rules = load_rules(load_json("assets/cfg/collisions.json"))
        self.explosions_cfg = load_json("assets/cfg/explosions.json")
        # Segundos que faltan para pasar a la siguiente escena tras morir (None: el jugador vive).
        self.death_left: float | None = None
        ServiceLocator.music.stop()
        self.camera = Camera(eng.world_size, eng.viewport)
        level = load_level(eng.level)
        # Velocidad del jugador (el hito 3 añade la aceleración); los enemigos van algo más rápido.
        self.player_speed = load_entity_cfg("player", ("max_speed",))["max_speed"]
        start = level["player_start"]
        self.player = create_player_placeholder(self.world, pygame.Vector2(start["x"], start["y"]))
        self.difficulty = difficulty_params(level)  # lo consumen spawn, steering y alertas
        factor = difficulty_factor(self.difficulty)  # 0..1 para núcleos, spawner y steering
        # Bases: las torretas disparan de cerca; el núcleo queda abierto o tiene ciclo según el nivel.
        self.cfg_bases = load_bases()
        for b in level["bases"]:
            create_base(self.world, pygame.Vector2(b["x"], b["y"]), b["orientation"],
                        self.cfg_bases, level["core_mode"], factor)
        # Enemigos I, P y E: salen alrededor del jugador a un ritmo que sube con la dificultad.
        self.cfg_enemies = load_enemies()
        create_enemy_spawner(self.world, self.cfg_enemies, factor)
        create_stars(self.world, eng.cfg_world, eng.viewport)
        self.round = level["round"]
        self.hud = Hud(ServiceLocator.fonts.get("main"), eng.state.cfg["life_icons_max"])
        self.level_total_bases = len(level["bases"])
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

    def bases_remaining(self) -> int:
        return sum(1 for _, t in self.world.get_component(CMinimapTrack) if t.kind == "base")

    def level_cleared(self) -> None:
        """Se destruyeron todas las bases: siguiente nivel o victoria."""
        self.engine.switch_scene(after_level_cleared(self.engine.state, level_numbers()))

    def player_died(self) -> None:
        """El jugador murió: pierde una vida y repite el nivel, o va a derrota."""
        self.engine.switch_scene(after_player_died(self.engine.state))

    def _update_player_death(self, delta_time: float) -> bool:
        """Si el jugador murió, espera a que se vea su explosión y luego pide la escena.

        Devuelve True cuando ya se pidió el cambio de escena.
        """
        if self.death_left is None:
            if self.world.entity_exists(self.player):
                return False
            self.death_left = self.explosions_cfg["player"]["death_wait"]
        self.death_left -= delta_time
        if self.death_left <= 0:
            self.player_died()
            return True
        return False

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
        # Con el jugador muerto (esperando su explosión) no hay posición que perseguir ni
        # a la que apuntar: el resto del mundo sigue, pero sin IA de enemigos ni torretas.
        player_alive = self.world.entity_exists(self.player)
        player_pos = None
        if player_alive:
            self.world.component_for_entity(self.player, CVelocity).vel = \
                self.direction * self.player_speed
            player_pos = self.world.component_for_entity(self.player, CTransform).pos
            system_enemy_spawner(self.world, player_pos, self.engine.world_size, self.cfg_enemies,
                                 self.player_speed, delta_time)
            system_enemy_state(self.world, player_pos, self.engine.world_size, delta_time)
            system_turrets(self.world, player_pos, self.engine.world_size, self.cfg_bases,
                           delta_time)
            system_base_cores(self.world, player_pos, self.engine.world_size, self.cfg_enemies,
                              self.player_speed, delta_time)
        system_movement(self.world, delta_time)
        system_wraparound(self.world, self.engine.world_size)
        system_enemy_bullets(self.world, self.engine.world_size, delta_time)
        collisions = system_collision(self.world, self.engine.world_size)
        system_collision_rules(self.world, collisions, self.collision_rules,
                               self.engine.world_size)
        system_explode(self.world, self.explosions_cfg)  # antes de borrar: aún hay posición
        system_animation(self.world, delta_time)
        system_destroy(self.world)
        if player_alive:
            system_enemy_despawn(self.world, player_pos, self.engine.world_size,
                                 self.cfg_enemies["spawn"]["despawn_distance"])
        system_camera_follow(self.world, self.camera)
        if self._update_player_death(delta_time):
            return
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
