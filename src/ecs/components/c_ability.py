import pygame


class CAbility:
    """Segunda habilidad especial de la nave (escudo): usos acumulados y límite.

    `charges` sube al recoger el ítem del mundo (hasta `max_charges`) y baja al activarla con X.
    `trigger` es la pulsación pendiente de X."""

    def __init__(self, max_charges: int, duration: float, charges: int = 0) -> None:
        self.max_charges = max_charges
        self.duration = duration
        self.charges = charges
        self.trigger = False


class CShield:
    """La nave está protegida: ninguna colisión la destruye ni destruye al otro. `remaining` en segundos."""

    def __init__(self, remaining: float) -> None:
        self.remaining = remaining


class CShieldAura:
    """Anillo que sigue a `owner` mientras tiene CShield; parpadea al final (`blank` = invisible)."""

    def __init__(self, owner: int, surf: pygame.Surface, blank: pygame.Surface,
                 blink_seconds: float, blink_rate: float) -> None:
        self.owner = owner
        self.surf = surf
        self.blank = blank
        self.blink_seconds = blink_seconds
        self.blink_rate = blink_rate


class CAbilityItem:
    """Ítem del mundo que da un uso de la habilidad al jugador que lo toca."""


class CItemSpawner:
    """Cada `interval` segundos tira un dado: con probabilidad `chance` (la define el nivel) aparece un ítem."""

    def __init__(self, interval: float, chance: float) -> None:
        self.interval = interval
        self.chance = chance
        self.timer = 0.0
