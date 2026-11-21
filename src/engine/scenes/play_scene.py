import pygame

from src.create.prefab_creator import (
    create_alert,
    create_base,
    create_enemy_spawner,
    create_player,
    create_special_shot_message,
    create_stars,
)
from src.create.prefab_obstacles import create_obstacles
from src.ecs.components.c_alert import CAlert
from src.ecs.components.c_invulnerable import CInvulnerable
from src.ecs.components.c_player_ship import CPlayerShip
from src.ecs.components.c_weapon import CWeapon
from src.ecs.components.c_minimap_track import CMinimapTrack
from src.ecs.components.c_transform import CTransform
from src.ecs.systems.s_alert import alert_base_destroyed, system_alert
from src.ecs.systems.s_animation import system_animation
from src.ecs.systems.s_base_behavior import system_base_cores, system_turrets
from src.ecs.systems.s_camera import system_camera_follow
from src.ecs.systems.s_lifetime import system_lifetime
from src.ecs.systems.s_collision import system_collision
from src.ecs.systems.s_collision_rules import load_rules, system_collision_rules
from src.ecs.systems.s_destroy import system_destroy
from src.ecs.systems.s_enemy_spawner import system_enemy_despawn, system_enemy_spawner
from src.ecs.systems.s_enemy_sprite import system_enemy_sprite
from src.ecs.systems.s_enemy_state import system_enemy_state
from src.ecs.systems.s_explode import create_explosion_group, system_explode
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
    load_level,
)
from src.engine.difficulty import difficulty_factor, difficulty_params
from src.engine.game_state import ALERTS
from src.engine.level_flow import after_level_cleared, after_player_died
from src.engine.input.command import Phase
from src.engine.menu import Menu
from src.engine.scenes.info_scene import draw_page, page_surfaces
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator, color_from_cfg
from src.engine.sfx import play_music, play_sound

# Opciones del menú (el mismo del título) que en la pausa abren una página de menu.json.
PAUSE_PAGES = {"INSTRUCTIONS": "instructions", "CREDITS": "credits"}


class PlayScene(Scene):
    """Escena de nivel: mundo, cámara, estrellas, minimapa, jugador, bases, obstáculos y enemigos."""

    panel_lives = True  # en partida se ven las vidas
    cheat_allowed = True  # la demo del modo atractor lo desactiva: ahí la nave sí puede morir
    # Al perder una vida el nivel sigue donde iba (bases destruidas y tiempo de alerta).
    # La demo del modo atractor no lee ni toca ese progreso.
    keeps_progress = True

    def do_create(self) -> None:
        eng = self.engine
        self.collision_rules = load_rules(load_json("assets/cfg/collisions.json"))
        self.explosions_cfg = load_json("assets/cfg/explosions.json")
        obstacles_cfg = load_json("assets/cfg/obstacles.json")
        # Segundos que faltan para pasar a la siguiente escena tras morir (None: el jugador vive).
        self.death_left: float | None = None
        self.camera = Camera(eng.world_size, eng.viewport)
        level = load_level(eng.level)
        self.play_level_music(level)
        # Velocidad máxima del jugador: los enemigos van algo más rápido que ella.
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
        self.difficulty = difficulty_params(level)  # tiempos de las alertas del nivel
        factor = difficulty_factor(self.difficulty)  # 0..1 para núcleos, spawner y steering
        # Bases: las torretas disparan de cerca; el núcleo queda abierto o tiene ciclo según el nivel.
        self.cfg_bases = load_bases()
        self.base_positions: dict[int, pygame.Vector2] = {}  # para la explosión al caer cada base
        self.base_index: dict[int, int] = {}  # entidad de la base -> su índice en el nivel
        destroyed = eng.state.bases_destroyed if self.keeps_progress else set()
        for i, b in enumerate(level["bases"]):
            if i in destroyed:
                continue  # cayó antes de perder la vida: no vuelve
            pos = pygame.Vector2(b["x"], b["y"])
            base = create_base(self.world, pos, b["orientation"], self.cfg_bases,
                               level["core_mode"], factor)
            self.base_positions[base] = pos
            self.base_index[base] = i
        create_obstacles(self.world, level, obstacles_cfg, eng.world_size)
        # Enemigos I, P y E: salen alrededor del jugador a un ritmo que sube con la dificultad.
        self.cfg_enemies = load_enemies()
        create_enemy_spawner(self.world, self.cfg_enemies, factor)
        # Alerta: VERDE al empezar (sin enemigos), AMARILLA al poco y ROJA si el nivel se alarga.
        self.alert = self.world.component_for_entity(
            create_alert(self.world, self.difficulty), CAlert)
        if self.keeps_progress:
            # Tras perder una vida vuelve a VERDE, pero el reloj hacia la ROJA no se reinicia.
            self.alert.elapsed = eng.state.level_seconds
        create_stars(self.world, eng.cfg_world, eng.viewport)
        self.round = level["round"]
        eng.state.alert = ALERTS[0]  # todo nivel empieza en verde
        self.level_total_bases = len(level["bases"])
        self._sync_invulnerable()  # la nave se recrea en cada nivel o vida: hereda el modo trampa
        self.camera.follow(pygame.Vector2(start["x"], start["y"]))
        self.camera.delta = pygame.Vector2()
        # Pausa: el mundo queda intacto y solo se congela; no se destruye nada.
        self.paused = False
        # Salir al título pierde el progreso: antes se pide confirmación (mundo congelado).
        self.confirm_exit = False
        white = color_from_cfg(eng.cfg_menu["colors"]["normal"])
        font = ServiceLocator.fonts.get("main")
        self.confirm_lines = [font.render(t, False, white) for t in eng.cfg_menu["exit_confirm"]]
        # En pausa se accede al mismo menú de opciones del título, más la salida al título.
        self.cfg_pause = eng.cfg_menu["pause"]
        self.pause_text = font.render(self.cfg_pause["title"], False, white)
        self.pause_menu = Menu(eng.cfg_menu["title_items"] + self.cfg_pause["extra_items"],
                               eng.cfg_menu["colors"], eng.cfg_menu["line_height"])
        self.pause_levels = level_numbers() or [eng.level]
        self.pause_level = eng.level  # el que marca NIVEL en el menú; solo se aplica con JUGAR
        self.pause_page: list | None = None  # página abierta desde la pausa (instrucciones, créditos)
        self.page_hint = font.render(self.cfg_pause["page_hint"], False,
                                     color_from_cfg(eng.cfg_menu["colors"]["selected"]))
        self._refresh_pause_level()
        # BLAST OFF!: al empezar el nivel el jugador no se mueve hasta que acaba la cuenta.
        blast = eng.cfg_world["blast_off"]
        self.blast_left = blast["seconds"]
        self.blast_text = ServiceLocator.fonts.get("main").render(
            blast["text"], False, pygame.Color(255, 255, 255)
        )
        play_sound("blast_off")

    def play_level_music(self, level: dict) -> None:
        """Música del nivel; si el nivel no define una registrada (o no hay audio), silencio."""
        play_music(level.get("music"))

    def _steer_ship(self, action: str, phase: Phase) -> None:
        """Dirección y disparo de la nave. Se registran siempre (también en pausa) para que
        soltar una tecla durante la pausa no deje la nave girando con una tecla fantasma."""
        if not self.world.entity_exists(self.player):
            return  # nave destruida (se ve su explosión): ya no hay a quién dirigir ni disparar
        if action in HEADING_KEYS:
            held = self.world.component_for_entity(self.player, CPlayerShip).held
            if phase == Phase.START:
                if self.blast_left <= 0:  # durante BLAST OFF! no se guarda la dirección
                    held.add(action)
            else:
                held.discard(action)
        elif action == "FIRE":
            weapon = self.world.component_for_entity(self.player, CWeapon)
            weapon.held = phase == Phase.START
            if weapon.held and not self.paused and self.blast_left <= 0:
                weapon.trigger = True

    def do_action(self, action: str, phase: Phase) -> None:
        self._steer_ship(action, phase)
        if phase != Phase.START:
            return
        if action == "EDITOR":
            # F2: editor de niveles (#44); allí F2 vuelve. El nivel puede cambiar: empieza de cero.
            self.engine.state.clear_level_progress()
            self.engine.switch_scene("EDITOR")
            return
        if action == "CHEAT":
            self.engine.state.cheat = not self.engine.state.cheat  # F1, también en pausa o BLAST OFF!
            self._sync_invulnerable()
            return
        if self.confirm_exit:
            if action == "SELECT":
                self.engine.switch_scene("TITLE")
            elif action == "BACK":
                self.confirm_exit = False  # ESC otra vez: cancela y vuelve a donde estaba
            return
        if action == "BACK":
            if self.pause_page is not None:
                self.pause_page = None  # ESC cierra la página y vuelve al menú de pausa
            else:
                self.confirm_exit = True  # ESC pide confirmar, jugando o en pausa
            return
        if action == "PAUSE":
            self.paused = not self.paused  # P alterna entre jugar y pausar
            self._reset_pause_menu()
            return
        if self.paused:
            self._pause_action(action)

    def _reset_pause_menu(self) -> None:
        """El menú de pausa siempre abre igual: en JUGAR, con el nivel actual y sin página."""
        self.pause_menu.selected = 0
        self.pause_page = None
        self.pause_level = self.engine.level
        self._refresh_pause_level()

    def _refresh_pause_level(self) -> None:
        self.pause_menu.set_label("LEVEL", f"NIVEL < {self.pause_level} >")

    def _pause_action(self, action: str) -> None:
        """Menú de pausa: el mismo del título. JUGAR reanuda (o empieza el nivel elegido en
        NIVEL, si se cambió), INSTRUCCIONES y CREDITOS se leen sin salir de la pausa, y la
        opción extra sale al título previa confirmación."""
        if self.pause_page is not None:
            if action == "SELECT":
                self.pause_page = None
            return
        if self.pause_menu.current_action == "LEVEL" and action in ("LEFT", "RIGHT"):
            levels = self.pause_levels
            index = levels.index(self.pause_level) if self.pause_level in levels else 0
            self.pause_level = levels[(index + (-1 if action == "LEFT" else 1)) % len(levels)]
            self._refresh_pause_level()
            return
        chosen = self.pause_menu.handle_action(action, Phase.START)
        if chosen == "PLAY":
            if self.pause_level == self.engine.level:
                self.paused = False
            else:  # otro nivel: partida nueva desde ahí, como al elegirlo en el título
                self.engine.level = self.pause_level
                self.engine.start_game()
                self.engine.switch_scene("CUTSCENE")
        elif chosen in PAUSE_PAGES:
            cfg = self.engine.cfg_menu
            self.pause_page = page_surfaces(cfg, cfg[PAUSE_PAGES[chosen]])
        elif chosen == "EXIT":
            self.confirm_exit = True

    def _sync_invulnerable(self) -> None:
        """Pone o quita CInvulnerable en la nave según el modo trampa (F1).

        Así las reglas de colisión no la destruyen: no hay muerte que ignorar después.
        """
        if not self.world.entity_exists(self.player):
            return
        has = self.world.try_component(self.player, CInvulnerable) is not None
        want = self.cheat_allowed and self.engine.state.cheat
        if want and not has:
            self.world.add_component(self.player, CInvulnerable())
        elif has and not want:
            self.world.remove_component(self.player, CInvulnerable)

    def _explode_destroyed_bases(self) -> None:
        """Una base cayó (sus seis torretas o un disparo al núcleo): explota donde estaba.

        damage_base_part la borra al instante, así que se la reconoce porque ya no existe.
        (Se evita el evento global BASE_DESTROYED de esper: sus manejadores son referencias
        débiles compartidas por todas las escenas y pueden romper un dispatch.)
        """
        for base in [b for b in self.base_positions if not self.world.entity_exists(b)]:
            if self.keeps_progress:
                self.engine.state.bases_destroyed.add(self.base_index[base])
            create_explosion_group(self.world, self.base_positions.pop(base), pygame.Vector2(),
                                   self.explosions_cfg["base"], self.explosions_cfg)
            if self.bases_remaining():  # con la última el nivel termina: sin cambio de alerta
                alert_base_destroyed(self.world)  # un respiro: vuelve a VERDE por un rato

    def bases_remaining(self) -> int:
        return sum(1 for _, t in self.world.get_component(CMinimapTrack) if t.kind == "base")

    def level_cleared(self) -> None:
        """Se destruyeron todas las bases: siguiente nivel o victoria."""
        self.engine.switch_scene(after_level_cleared(self.engine.state, level_numbers()))

    def player_died(self) -> None:
        """El jugador murió: pierde una vida y vuelve al nivel (que conserva su progreso), o va a derrota."""
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
        if self.paused or self.confirm_exit:
            # En pausa solo las estrellas siguen brillando, quietas (sin parallax ni movimiento).
            system_star_blink(self.world, delta_time)
            return
        if self.blast_left > 0:
            self.blast_left = max(0.0, self.blast_left - delta_time)
            system_star_blink(self.world, delta_time)
            return
        system_lifetime(self.world, delta_time)
        system_alert(self.world, delta_time)  # antes del spawner y los núcleos, que la consultan
        self.engine.state.alert = self.alert.level.name  # la barra (CONDITION) muestra la alerta del nivel
        if self.keeps_progress:
            self.engine.state.level_seconds = self.alert.elapsed
        system_player_movement(self.world, delta_time)
        system_player_sprite(self.world)
        system_player_fire(self.world, delta_time)
        # Con el jugador muerto (esperando su explosión) no hay posición que perseguir ni
        # a la que apuntar: el resto del mundo sigue, pero sin IA de enemigos ni torretas.
        player_alive = self.world.entity_exists(self.player)
        player_pos = None
        if player_alive:
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
        collisions = system_collision(self.world, self.engine.world_size)
        points = system_collision_rules(self.world, collisions, self.collision_rules,
                                        self.engine.world_size,
                                        self.engine.cfg_world["score_popup"])
        if points:
            lives = self.engine.state.lives
            self.engine.state.add_score(points)
            if self.engine.state.lives > lives:
                play_sound("extra_life")
        system_enemy_sprite(self.world)  # tras las colisiones: usa la velocidad final del fotograma
        system_explode(self.world, self.explosions_cfg)  # antes de borrar: aún hay posición
        system_animation(self.world, delta_time)
        system_destroy(self.world)
        self._explode_destroyed_bases()
        if player_alive:
            system_enemy_despawn(self.world, player_pos, self.engine.world_size,
                                 self.cfg_enemies["spawn"]["despawn_distance"])
        system_camera_follow(self.world, self.camera)
        system_bullet_cleanup(self.world, self.camera, self.player_cfg["weapon"]["offscreen_margin"])
        if self._update_player_death(delta_time):
            return
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

    def panel_round(self) -> int:
        return self.round

    def do_clean(self) -> None:
        self.engine.state.alert = ALERTS[0]  # fuera de la partida, CONDITION está en verde
        super().do_clean()

    def draw_radar(self, screen: pygame.Surface) -> None:
        """El radar con sus marcas. En pausa y al confirmar la salida desaparecen y queda el marco."""
        if self.paused or self.confirm_exit:
            super().draw_radar(screen)
            return
        system_minimap_rendering(self.world, screen, self.engine.cfg_world["minimap"],
                                 self.engine.world_size)

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
            # Desaparecen jugador, bases, interfaz y minimapa; quedan el fondo, el aviso y el menú.
            stage = self.engine.viewport
            if self.pause_page is not None:
                draw_page(screen, stage, self.pause_page, self.page_hint)
                return
            screen.blit(self.pause_text, self.pause_text.get_rect(
                center=(stage.centerx, stage.top + self.cfg_pause["title_y"])))
            self.pause_menu.draw(screen, stage.centerx, stage.top + self.cfg_pause["menu_top"])
            return
        system_world_rendering(self.world, screen, self.camera)
        system_rendering(self.world, screen)
        if self.blast_left > 0:
            screen.blit(
                self.blast_text,
                self.blast_text.get_rect(center=self.engine.viewport.center),
            )
