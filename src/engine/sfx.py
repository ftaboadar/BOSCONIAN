"""Efectos de sonido por evento: suenan solo si están registrados en resources.json."""

import pygame

from src.engine.service_locator import ServiceLocator


def play_sound(name: str) -> None:
    """Reproduce un sonido de resources.json; si no se puede, no hace nada.

    No suena (sin error) si el sonido no está registrado, si los servicios aún no se
    iniciaron (por ejemplo, un Menu en pruebas) o si no hay audio disponible (un equipo
    sin salida de sonido). Así un sonido nunca tira el juego.
    """
    sounds = getattr(ServiceLocator, "sounds", None)
    if sounds is not None and sounds.has(name) and pygame.mixer.get_init():
        sounds.play(name)
