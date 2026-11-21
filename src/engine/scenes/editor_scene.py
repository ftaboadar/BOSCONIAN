"""Escena del editor de niveles (#44): se entra y se sale con F2 desde el juego."""

import pygame

from src.engine.data_loader import load_json
from src.engine.input.command import Phase
from src.engine.level_editor import LevelEditor
from src.engine.scenes.scene import Scene
from src.engine.service_locator import ServiceLocator, color_from_cfg

REPEAT_DELAY = 0.25  # al mantener una flecha, tarda esto en empezar a repetirse...
REPEAT_RATE = 0.05   # ...y luego se mueve cada tanto
MESSAGE_SECONDS = 2.0
DIRECTIONS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
PANEL_X = 184
HELP = [("FLECHAS", "MOVER"), ("ENTER", "BASE"), ("Z", "BORRAR"), ("X", "GIRAR"),
        ("P", "INICIO"), ("S", "GUARDAR"), ("L", "CARGAR"), ("PGUP/DN", "NIVEL"),
        ("D", "DIFICULTAD"), ("M", "MUSICA"), ("T", "HABILIDAD"), ("F2/ESC", "SALIR"),
        ("H", "CERRAR")]
HELP_KEY_WIDTH = 8  # caracteres de la columna de teclas

BG = pygame.Color(0, 0, 40)
GRID = pygame.Color(30, 30, 90)
BORDER = pygame.Color(255, 255, 255)
BASE_COLOR = pygame.Color(255, 64, 64)
START_COLOR = pygame.Color(255, 255, 255)
CURSOR_OK = pygame.Color(255, 220, 0)
CURSOR_BAD = pygame.Color(255, 64, 64)


class EditorScene(Scene):
    """Edita el nivel actual sobre el mapa del mundo entero a escala.

    El modelo (LevelEditor) hace las ediciones y el acceso a archivos; esta escena solo
    traduce teclas y dibuja. Al salir se vuelve al nivel: se juega lo que esté guardado."""

    def do_create(self) -> None:
        eng = self.engine
        tracks = [name for name in load_json("assets/cfg/resources.json")["music"] if name != "title"]
        self.editor = LevelEditor(eng.world_size, tracks, eng.level)
        self.editor.cursor = pygame.Vector2(self.editor.start_pos)
        self.font = ServiceLocator.fonts.get("main")
        colors = eng.cfg_menu["colors"]
        self.title_color = color_from_cfg(colors["title"])
        self.normal_color = color_from_cfg(colors["normal"])
        self.selected_color = color_from_cfg(colors["selected"])
        # El mapa muestra el mundo entero dentro del viewport, bajo la barra del título.
        side = min(eng.viewport.w, eng.viewport.h - 32)
        self.map_rect = pygame.Rect(0, 16, side, side)
        self.scale = side / eng.world_size.x
        self.message = ""
        self.message_left = 0.0
        self.show_help = False
        self.repeat: dict[str, float] = {}  # flecha mantenida -> segundos hasta el próximo paso
        ServiceLocator.music.stop()

    # --- entrada --------------------------------------------------------------------------

    def say(self, message: str) -> None:
        self.message, self.message_left = message, MESSAGE_SECONDS

    def leave(self) -> None:
        """Vuelve al nivel. Si se cambió de número, se juega ese, siempre que exista guardado."""
        if self.editor.exists():
            self.engine.level = self.editor.number
        self.engine.switch_scene("PLAY")

    def do_action(self, action: str, phase: Phase) -> None:
        if action in DIRECTIONS:
            if phase == Phase.START:
                self.editor.move_cursor(*DIRECTIONS[action])
                self.repeat[action] = REPEAT_DELAY
            else:
                self.repeat.pop(action, None)
            return
        if phase != Phase.START:
            return
        ed = self.editor
        commands = {"SELECT": ed.place_base, "FIRE": ed.delete_base, "SPECIAL": ed.rotate,
                    "PAUSE": ed.set_start, "EDIT_SAVE": ed.save, "EDIT_LOAD": ed.load,
                    "EDIT_PREV": lambda: ed.goto(-1), "EDIT_NEXT": lambda: ed.goto(1),
                    "EDIT_DIFFICULTY": ed.cycle_difficulty, "EDIT_MUSIC": ed.cycle_music,
                    "EDIT_SPECIAL": ed.toggle_special}
        if action in ("EDITOR", "BACK"):
            self.leave()
        elif action == "EDIT_HELP":
            self.show_help = not self.show_help
        elif action in commands:
            self.say(commands[action]())

    def do_update(self, delta_time: float) -> None:
        self.message_left = max(0.0, self.message_left - delta_time)
        for action, left in list(self.repeat.items()):
            left -= delta_time
            while left <= 0:
                self.editor.move_cursor(*DIRECTIONS[action])
                left += REPEAT_RATE
            self.repeat[action] = left

    # --- dibujo ---------------------------------------------------------------------------

    def to_screen(self, pos) -> tuple[int, int]:
        return (round(self.map_rect.x + pos[0] * self.scale), round(self.map_rect.y + pos[1] * self.scale))

    def scaled_rect(self, rect: pygame.Rect) -> pygame.Rect:
        x, y = self.to_screen(rect.topleft)
        return pygame.Rect(x, y, max(2, round(rect.w * self.scale)), max(2, round(rect.h * self.scale)))

    def text(self, screen: pygame.Surface, text: str, color: pygame.Color, x: int, y: int,
             center: bool = False) -> None:
        surf = self.font.render(text, False, color)
        screen.blit(surf, surf.get_rect(center=(x, y)) if center else (x, y))

    def do_draw(self, screen: pygame.Surface) -> None:
        ed = self.editor
        screen.fill(pygame.Color(0, 0, 0))
        pygame.draw.rect(screen, BG, self.map_rect)
        step = round(128 * self.scale)
        for i in range(1, 8):  # rejilla cada 128 px del mundo
            pygame.draw.line(screen, GRID, (self.map_rect.x + i * step, self.map_rect.top),
                             (self.map_rect.x + i * step, self.map_rect.bottom - 1))
            pygame.draw.line(screen, GRID, (self.map_rect.left, self.map_rect.y + i * step),
                             (self.map_rect.right - 1, self.map_rect.y + i * step))
        pygame.draw.rect(screen, BORDER, self.map_rect, 1)
        for base in ed.level["bases"]:
            self._draw_base(screen, base, BASE_COLOR)
        sx, sy = self.to_screen(ed.start_pos)
        pygame.draw.polygon(screen, START_COLOR, [(sx, sy - 4), (sx + 3, sy + 3), (sx - 3, sy + 3)])
        self._draw_cursor(screen)
        pygame.draw.rect(screen, pygame.Color(0, 0, 0), (0, 0, self.engine.viewport.w, 16))
        mark = "*" if ed.dirty else ""
        self.text(screen, f"EDITOR NIVEL {ed.number:02d}{mark}", self.title_color, 4, 4)
        self._draw_panel(screen)
        if self.message_left > 0:
            self.text(screen, self.message, self.selected_color, self.map_rect.centerx,
                      self.map_rect.bottom + 8, center=True)
        if self.show_help:
            self._draw_help(screen)

    def _draw_base(self, screen: pygame.Surface, base: dict, color: pygame.Color) -> None:
        """Contorno de la base y una línea por su eje abierto (el del disparo al núcleo)."""
        rect = self.scaled_rect(self.editor.footprint(base))
        pygame.draw.rect(screen, color, rect, 1)
        if base["orientation"] == "vertical":
            pygame.draw.line(screen, color, (rect.centerx, rect.top), (rect.centerx, rect.bottom - 1))
        else:
            pygame.draw.line(screen, color, (rect.left, rect.centery), (rect.right - 1, rect.centery))

    def _draw_cursor(self, screen: pygame.Surface) -> None:
        ed = self.editor
        on_base = ed.base_at(ed.cursor) is not None
        color = CURSOR_OK if on_base or ed.placement_error() is None else CURSOR_BAD
        if not on_base:  # sombra de la base que se pondría
            self._draw_base(screen, ed.ghost(), color)
        cx, cy = self.to_screen(ed.cursor)
        pygame.draw.line(screen, color, (cx - 4, cy), (cx + 4, cy))
        pygame.draw.line(screen, color, (cx, cy - 4), (cx, cy + 4))

    def _draw_panel(self, screen: pygame.Surface) -> None:
        ed = self.editor
        music = ed.level.get("music")
        lines = [("NIVEL", self.title_color), (f"{ed.number:02d}", self.normal_color),
                 ("DIF", self.title_color), (str(ed.level.get("difficulty", 1)), self.normal_color),
                 ("HABIL", self.title_color), ("SI" if ed.level.get("special_shot") else "NO", self.normal_color),
                 ("MUSICA", self.title_color), ((music or "NINGUNA")[:9].upper(), self.normal_color),
                 ("BASES", self.title_color), (f"{len(ed.level['bases'])}", self.normal_color),
                 ("NUEVAS", self.title_color), (ed.orientation[:5].upper(), self.normal_color),
                 ("H: AYUDA", self.selected_color)]
        for i, (text, color) in enumerate(lines):
            self.text(screen, text, color, PANEL_X, 20 + i * 12)

    def _draw_help(self, screen: pygame.Surface) -> None:
        box = self.map_rect.inflate(-8, -8)
        pygame.draw.rect(screen, pygame.Color(0, 0, 0), box)
        pygame.draw.rect(screen, BORDER, box, 1)
        for i, line in enumerate(HELP):  # (tecla, qué hace)
            self.text(screen, line[0].ljust(HELP_KEY_WIDTH) + line[1], self.normal_color,
                      box.x + 4, box.y + 6 + i * 12)
