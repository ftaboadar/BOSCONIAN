"""Patrón Escena: cada escena tiene su propio mundo ECS y ciclo de vida."""

import esper
import pygame

from src.engine.input.command import Phase


class Scene:
    def __init__(self, engine) -> None:
        self.engine = engine
        self.world = esper.World()

    def do_create(self) -> None:
        """Crea entidades y arranca recursos de la escena."""

    def do_action(self, action: str, phase: Phase) -> None:
        """Recibe una acción lógica del input."""

    def do_update(self, delta_time: float) -> None:
        """Ejecuta los sistemas de la escena."""

    def do_draw(self, screen: pygame.Surface) -> None:
        """Dibuja la escena."""

    def do_clean(self) -> None:
        """Libera la escena."""
        self.world.clear_database()
