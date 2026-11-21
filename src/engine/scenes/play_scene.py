import pygame

from src.create.prefab_creator import (
    create_base,
    create_enemy_spawner,
    create_player,
    create_special_shot_message,
    create_stars,
)
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_weapon import CWeapon
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_base_behavior import system_base_cores, system_turrets
from src.ecs.systems.s_camera import system_camera_follow
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_enemy_bullet import system_enemy_bullets
from src.ecs.systems.s_enemy_spawner import system_enemy_despawn, system_enemy_spawner
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_minimap import system_minimap_rendering
from src.ecs.systems.s_movement import system_movement
from src.ecs.systems.s_player import (
    HEADING_KEYS,
    system_player_movement,
    system_player_sprite,
)
from src.ecs.systems.s_rendering import system_rendering, system_world_rendering
from src.ecs.systems.s_star import (
    system_star_blink,
    system_star_parallax,
    system_star_rendering,
)
from src.ecs.systems.s_weapon import system_bullet_cleanup, system_player_fire
from src.ecs.systems.s_wraparound import system_wraparound
from src.engine.camera import Camera
from src.engine.data_loader import (
      level_numbers, 
      load_bases, 
      load_enemies, 
      load_entity_cfg, 
      load_json, 
      load_level
    )
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
        ServiceLocator.music.stop()
        self.camera = Camera(eng.world_size, eng.viewport)
        level = load_level(eng.level)
        # Velocidad del jugador (el hito 3 añade la aceleración); los enemigos van algo más rápido.
        self.player_speed = load_entity_cfg("player", ("max_speed",))["max_speed"]
        start = level["player_start"]
        self.player_cfg = load_json("assets/cfg/player.json")
        self.player = create_player(
            self.world,
            pygame.Vector2(start["x"], start["y"]),
            self.player_cfg,
            level["special_shot"],
        )
        create_special_shot_message(
            self.world, self.player_cfg, level["special_shot"], eng.viewport.centerx
        )
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
        # Pausa: el mundo queda intacto y solo se congela; no se destruye nada.
        self.paused = False
        # Salir al título pierde el progreso: antes se pide confirmación (mundo congelado).
        self.confirm_exit = False
        white = pygame.Color(255, 255, 255)
        font = ServiceLocator.fonts.get("main")
        self.confirm_lines = [font.render(t, False, white) for t in eng.cfg_menu["exit_confirm"]]
        self.pause_text = ServiceLocator.fonts.get("main").render(
            "JUEGO PAUSADO", False, pygame.Color(255, 255, 255)
        )
        # BLAST OFF!: al empezar el nivel el jugador no se mueve hasta que acaba la cuenta.
        blast = eng.cfg_world["blast_off"]
        self.blast_left = blast["seconds"]
        self.blast_text = ServiceLocator.fonts.get("main").render(
            blast["text"], False, pygame.Color(255, 255, 255)
        )
        if ServiceLocator.sounds.has("blast_off"):
            ServiceLocator.sounds.play("blast_off")

    def do_action(self, action: str, phase: Phase) -> None:
        if action in HEADING_KEYS:
            # Las teclas de dirección se registran siempre (también en pausa) para que
            # soltar una tecla durante la pausa no deje la nave girando con una tecla fantasma.
            held = self.world.component_for_entity(self.player, CPlayerShip).held
            if phase == Phase.START:
                if self.blast_left <= 0:  # durante BLAST OFF! no se guarda la dirección
                    held.add(action)
            else:
                held.discard(action)
            return
        if action == "FIRE":
            # Como las direcciones, se registra también en pausa para no perder el soltar la tecla.
            weapon = self.world.component_for_entity(self.player, CWeapon)
            weapon.held = phase == Phase.START
            if weapon.held and not self.paused and self.blast_left <= 0:
                weapon.trigger = True
            return
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
        if self.paused and action == "SELECT":
            # Acceso al título desde la pausa (#27 lo convertirá en el menú de opciones).
            self.confirm_exit = True
            return

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
        if self.paused or self.confirm_exit:
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
        player_pos = self.world.component_for_entity(self.player, CTransform).pos
        system_enemy_spawner(self.world, player_pos, self.engine.world_size, self.cfg_enemies,
                             self.player_speed, delta_time)
        system_enemy_state(self.world, player_pos, self.engine.world_size, delta_time)
        system_turrets(self.world, player_pos, self.engine.world_size, self.cfg_bases, delta_time)
        system_base_cores(self.world, player_pos, self.engine.world_size, self.cfg_enemies,
                          self.player_speed, delta_time)
        system_movement(self.world, delta_time)
        system_wraparound(self.world, self.engine.world_size)
        system_enemy_bullets(self.world, self.engine.world_size, delta_time)
        collisions = system_collision(self.world, self.engine.world_size)
        system_collision_rules(self.world, collisions, self.collision_rules,
                               self.engine.world_size)
        system_destroy(self.world)
        system_enemy_despawn(self.world, player_pos, self.engine.world_size,
                             self.cfg_enemies["spawn"]["despawn_distance"])
        system_camera_follow(self.world, self.camera)
        system_bullet_cleanup(self.world, self.camera, self.player_cfg["weapon"]["offscreen_margin"])
        if self.level_total_bases and self.bases_remaining() == 0:
            self.level_cleared()
            return
        system_star_blink(self.world, delta_time)
        system_star_parallax(
            self.world,
            self.engine.viewport,
            self.camera.delta,
            self.engine.cfg_world["stars_parallax_factor"],
        )

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
            screen.blit(
                self.pause_text,
                self.pause_text.get_rect(center=self.engine.viewport.center),
            )
            return
        system_world_rendering(self.world, screen, self.camera)
        system_rendering(self.world, screen)
        system_minimap_rendering(self.world, screen, self.engine.cfg_world["minimap"],
                                 self.engine.world_size)
        self.hud.draw(screen, self.engine.state, self.round)
        if self.blast_left > 0:
            screen.blit(
                self.blast_text,
                self.blast_text.get_rect(center=self.engine.viewport.center),
            )
