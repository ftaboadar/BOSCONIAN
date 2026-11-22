"""Patrón Command simplificado: tecla o control físico -> acción lógica."""

from enum import Enum

import pygame


class Phase(Enum):
    START = 1
    END = 2


Command = tuple[str, Phase]


class CommandMap:
    """Traduce eventos de teclado y gamepad a (acción, fase) según la configuración.

    Teclado y gamepad producen las mismas acciones lógicas, así las escenas no distinguen
    el origen y se puede alternar entre ambos en cualquier momento.
    """

    def __init__(self, keyboard_cfg: dict, gamepad_cfg: dict | None = None) -> None:
        self._key_to_action = {
            getattr(pygame, key_name): action
            for action, key_name in keyboard_cfg.items()
        }
        gamepad_cfg = gamepad_cfg or {}
        # Un botón puede disparar varias acciones (p. ej. A/X: FIRE y SELECT).
        self._button_to_actions = {
            int(button): [actions] if isinstance(actions, str) else list(actions)
            for button, actions in gamepad_cfg.get("buttons", {}).items()
        }
        self._deadzone = gamepad_cfg.get("deadzone", 0.5)
        self._axis_x = gamepad_cfg.get("axis_x", 0)
        self._axis_y = gamepad_cfg.get("axis_y", 1)
        # Dirección lógica sostenida por cada gamepad: {id: {"x": -1|0|1, "y": -1|0|1}}.
        self._held_dir: dict[int, dict[str, int]] = {}

    def translate(self, event: pygame.event.Event) -> list[Command]:
        """Comandos que produce un evento; lista vacía si no mapea a ninguno."""
        if event.type in (pygame.KEYDOWN, pygame.KEYUP):
            action = self._key_to_action.get(event.key)
            if action is None:
                return []
            return [(action, Phase.START if event.type == pygame.KEYDOWN else Phase.END)]
        if event.type in (pygame.JOYBUTTONDOWN, pygame.JOYBUTTONUP):
            phase = Phase.START if event.type == pygame.JOYBUTTONDOWN else Phase.END
            return [(action, phase) for action in self._button_to_actions.get(event.button, [])]
        if event.type == pygame.JOYAXISMOTION:
            if event.axis == self._axis_x:
                return self._set_direction(self._pad_id(event), "x", self._to_dir(event.value))
            if event.axis == self._axis_y:
                return self._set_direction(self._pad_id(event), "y", self._to_dir(event.value))
            return []
        if event.type == pygame.JOYHATMOTION:
            pad = self._pad_id(event)
            return (self._set_direction(pad, "x", event.value[0])
                    + self._set_direction(pad, "y", -event.value[1]))  # el hat tiene y positiva hacia arriba
        if event.type == pygame.JOYDEVICEREMOVED:
            return self._release_all(event.instance_id)
        return []

    @staticmethod
    def _pad_id(event: pygame.event.Event) -> int:
        return getattr(event, "instance_id", getattr(event, "joy", 0))

    def _to_dir(self, value: float) -> int:
        if value <= -self._deadzone:
            return -1
        if value >= self._deadzone:
            return 1
        return 0

    def _set_direction(self, pad: int, axis: str, new: int) -> list[Command]:
        """Compara la dirección nueva con la sostenida y emite solo las transiciones."""
        held = self._held_dir.setdefault(pad, {"x": 0, "y": 0})
        old = held[axis]
        if new == old:
            return []
        held[axis] = new
        names = {"x": ("LEFT", "RIGHT"), "y": ("UP", "DOWN")}[axis]
        commands: list[Command] = []
        if old != 0:
            commands.append((names[0 if old < 0 else 1], Phase.END))
        if new != 0:
            commands.append((names[0 if new < 0 else 1], Phase.START))
        return commands

    def _release_all(self, pad: int) -> list[Command]:
        """Si el gamepad se desconecta con el stick inclinado, suelta sus direcciones."""
        commands = self._set_direction(pad, "x", 0) + self._set_direction(pad, "y", 0)
        self._held_dir.pop(pad, None)
        return commands
