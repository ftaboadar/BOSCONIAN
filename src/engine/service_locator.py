"""Service locator: punto único de acceso a recursos y configuración."""

import json

import pygame


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def color_from_cfg(cfg: dict) -> pygame.Color:
    """Convierte {"r","g","b"} del JSON en pygame.Color leyendo cada canal por nombre,
    así el orden de las claves en el archivo no cambia el color."""
    return pygame.Color(cfg["r"], cfg["g"], cfg["b"])


class _Images:
    def __init__(self, paths: dict) -> None:
        self._paths = paths
        self._cache: dict[str, pygame.Surface] = {}

    def get(self, name: str) -> pygame.Surface:
        if name not in self._cache:
            self._cache[name] = pygame.image.load(self._paths[name]).convert_alpha()
        return self._cache[name]


class _Sounds:
    def __init__(self, paths: dict) -> None:
        self._paths = paths
        self._cache: dict[str, pygame.mixer.Sound] = {}

    def play(self, name: str) -> None:
        if name not in self._cache:
            self._cache[name] = pygame.mixer.Sound(self._paths[name])
        self._cache[name].play()


class _Music:
    def __init__(self, paths: dict) -> None:
        self._paths = paths
        self._current: str | None = None

    def play(self, name: str, loops: int = -1) -> None:
        if name == self._current:
            return
        pygame.mixer.music.load(self._paths[name])
        pygame.mixer.music.play(loops)
        self._current = name

    def stop(self) -> None:
        pygame.mixer.music.stop()
        self._current = None


class _Fonts:
    def __init__(self, specs: dict) -> None:
        self._specs = specs
        self._cache: dict[str, pygame.font.Font] = {}

    def get(self, name: str = "main") -> pygame.font.Font:
        if name not in self._cache:
            spec = self._specs[name]
            self._cache[name] = pygame.font.Font(spec["path"], spec["size"])
        return self._cache[name]


class ServiceLocator:
    """Registro global de servicios. Se inicializa una vez en el motor."""

    images: _Images
    sounds: _Sounds
    music: _Music
    fonts: _Fonts

    @classmethod
    def init(cls, resources_cfg: dict) -> None:
        cls.images = _Images(resources_cfg.get("images", {}))
        cls.sounds = _Sounds(resources_cfg.get("sounds", {}))
        cls.music = _Music(resources_cfg.get("music", {}))
        cls.fonts = _Fonts(resources_cfg.get("fonts", {}))
