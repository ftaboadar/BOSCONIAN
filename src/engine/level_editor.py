"""Modelo del editor de niveles (#44): edita un nivel en memoria y lo carga y guarda en
assets/cfg/levels. No depende de pygame más que por Vector2, para poder probarlo sin pantalla."""

import copy

import pygame

from src.engine import data_loader
from src.engine.data_loader import ConfigError, load_json

STEP = 16        # el cursor se mueve de a 16 px del mundo
MAX_BASES = 12   # más bases que esto no caben en un mundo de 1024x1024 sin amontonarse
MIN_LEVEL, MAX_LEVEL = 1, 99  # level_XX.json tiene dos dígitos


class LevelEditor:
    """Un nivel en edición: bases (rotadas o no), punto de partida y opciones.

    Cada operación devuelve un mensaje corto para mostrar al usuario ("BASE PUESTA",
    "OCUPADO"...). Nada toca el disco hasta guardar()."""

    def __init__(self, world_size: pygame.Vector2, tracks: list[str], number: int) -> None:
        self.world_size = pygame.Vector2(world_size)
        self.tracks = list(tracks)  # pistas de música disponibles para el nivel
        self.difficulties = sorted(int(k) for k in load_json("assets/cfg/difficulty.json")["levels"])
        hitbox = load_json("assets/cfg/collisions.json")["hitboxes"]["base"]["size"]
        self.base_size = pygame.Vector2(hitbox["w"], hitbox["h"])  # de la base vertical
        self.orientation = "vertical"  # con la que se ponen las bases nuevas
        self.cursor = self.world_size / 2
        self.number = number
        self.level: dict = {}
        self.dirty = False
        self.load(number)

    # --- cursor ---------------------------------------------------------------------------

    def move_cursor(self, dx: int, dy: int) -> None:
        pos = self.cursor + pygame.Vector2(dx, dy) * STEP
        self.cursor = pygame.Vector2(min(max(pos.x, 0), self.world_size.x - 1),
                                     min(max(pos.y, 0), self.world_size.y - 1))

    # --- geometría ------------------------------------------------------------------------

    def footprint(self, base: dict) -> pygame.Rect:
        """Rectángulo que ocupa una base en el mundo (la horizontal es la vertical girada)."""
        w, h = self.base_size
        if base["orientation"] == "horizontal":
            w, h = h, w
        rect = pygame.Rect(0, 0, int(w), int(h))
        rect.center = (int(base["x"]), int(base["y"]))
        return rect

    def base_at(self, pos: pygame.Vector2) -> int | None:
        """Índice de la base que cubre `pos`, o None."""
        for i, base in enumerate(self.level["bases"]):
            if self.footprint(base).collidepoint(pos.x, pos.y):
                return i
        return None

    def ghost(self) -> dict:
        """La base que se pondría ahora: en el cursor y con la orientación elegida."""
        return {"x": int(self.cursor.x), "y": int(self.cursor.y), "orientation": self.orientation}

    def _overlaps(self, rect: pygame.Rect, ignore: int | None = None) -> bool:
        return any(rect.colliderect(self.footprint(b))
                   for i, b in enumerate(self.level["bases"]) if i != ignore)

    def placement_error(self) -> str | None:
        """Por qué no se puede poner una base en el cursor (None si se puede)."""
        base = self.ghost()
        rect = self.footprint(base)
        if len(self.level["bases"]) >= MAX_BASES:
            return "DEMASIADAS BASES"
        if self._overlaps(rect):
            return "OCUPADO"
        if rect.collidepoint(self.start_pos.x, self.start_pos.y):
            return "ES EL INICIO"
        return None

    # --- edición --------------------------------------------------------------------------

    def place_base(self) -> str:
        error = self.placement_error()
        if error:
            return error
        self.level["bases"].append(self.ghost())
        self.dirty = True
        return "BASE PUESTA"

    def delete_base(self) -> str:
        index = self.base_at(self.cursor)
        if index is None:
            return "NO HAY BASE"
        del self.level["bases"][index]
        self.dirty = True
        return "BASE BORRADA"

    def rotate(self) -> str:
        """Gira la base que hay bajo el cursor; si no hay, cambia con la que se ponen las nuevas."""
        flip = {"vertical": "horizontal", "horizontal": "vertical"}
        index = self.base_at(self.cursor)
        if index is None:
            self.orientation = flip[self.orientation]
            return f"NUEVAS {self.orientation.upper()}"
        base = self.level["bases"][index]
        turned = dict(base, orientation=flip[base["orientation"]])
        if self._overlaps(self.footprint(turned), ignore=index):
            return "OCUPADO"
        base["orientation"] = turned["orientation"]
        self.dirty = True
        return f"BASE {base['orientation'].upper()}"

    @property
    def start_pos(self) -> pygame.Vector2:
        start = self.level["player_start"]
        return pygame.Vector2(start["x"], start["y"])

    def set_start(self) -> str:
        if self.base_at(self.cursor) is not None:
            return "OCUPADO"
        self.level["player_start"] = {"x": int(self.cursor.x), "y": int(self.cursor.y)}
        self.dirty = True
        return "INICIO PUESTO"

    def cycle_difficulty(self) -> str:
        current = self.level.get("difficulty", self.difficulties[0])
        later = [d for d in self.difficulties if d > current]
        self.level["difficulty"] = later[0] if later else self.difficulties[0]
        self.dirty = True
        return f"DIFICULTAD {self.level['difficulty']}"

    def cycle_music(self) -> str:
        options = [None] + self.tracks
        current = self.level.get("music")
        nxt = options[(options.index(current) + 1) % len(options)] if current in options else None
        if nxt is None:
            self.level.pop("music", None)
        else:
            self.level["music"] = nxt
        self.dirty = True
        return f"MUSICA {nxt or 'NINGUNA'}"[:20].upper()

    def toggle_special(self) -> str:
        self.level["special_shot"] = not self.level.get("special_shot", False)
        self.dirty = True
        return "HABILIDAD " + ("SI" if self.level["special_shot"] else "NO")

    # --- archivos -------------------------------------------------------------------------

    def exists(self, number: int | None = None) -> bool:
        return (self.number if number is None else number) in data_loader.level_numbers()

    def new_level(self, number: int) -> None:
        """Nivel vacío: una ronda por número, la nave al centro y sin bases todavía."""
        self.number = number
        self.level = {"round": number, "difficulty": self.difficulties[0], "core_mode": "open",
                      "player_start": {"x": int(self.world_size.x / 2), "y": int(self.world_size.y / 2)},
                      "bases": [], "obstacles": {}, "special_shot": False}
        self.dirty = False

    def load(self, number: int | None = None) -> str:
        """Carga el nivel `number` del disco (descartando lo editado); si no existe, uno nuevo."""
        number = self.number if number is None else number
        if not self.exists(number):
            self.new_level(number)
            return "NIVEL NUEVO"
        try:
            self.level = data_loader.load_level(number)
        except ConfigError:
            self.new_level(number)
            return "ARCHIVO INVALIDO"
        self.number = number
        self.dirty = False
        return "CARGADO"

    def goto(self, step: int) -> str:
        """Pasa al nivel anterior o siguiente, cargándolo del disco (o nuevo si no existe)."""
        number = min(max(self.number + step, MIN_LEVEL), MAX_LEVEL)
        return self.load(number)

    def save(self) -> str:
        if not self.level["bases"]:
            return "FALTAN BASES"  # sin bases el nivel nunca se podría pasar
        try:
            data_loader.save_level(self.number, copy.deepcopy(self.level))
        except (ConfigError, OSError):
            return "NO SE PUDO GUARDAR"
        self.dirty = False
        return "GUARDADO"
