"""Patrón Command simplificado: tecla física -> acción lógica."""

from enum import Enum

import pygame


class Phase(Enum):
    START = 1
    END = 2


class CommandMap:
    """Traduce eventos de teclado a (acción, fase) según la configuración."""

    def __init__(self, keyboard_cfg: dict) -> None:
        self._key_to_action = {
            getattr(pygame, key_name): action
            for action, key_name in keyboard_cfg.items()
        }

    def translate(self, event: pygame.event.Event) -> tuple[str, Phase] | None:
        if event.type not in (pygame.KEYDOWN, pygame.KEYUP):
            return None
        action = self._key_to_action.get(event.key)
        if action is None:
            return None
        phase = Phase.START if event.type == pygame.KEYDOWN else Phase.END
        return action, phase
