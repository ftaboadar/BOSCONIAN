import pygame


class CWeapon:
    """Arma de la nave: una bala hacia adelante y otra hacia atrás; mantener FIRE repite el disparo.

    `special` (definido por el nivel) habilita el disparo especial, que se usa con SPECIAL (X): tres balas al frente,
    separadas `special_spread` px, y una atrás. FIRE (Z) siempre dispara el disparo normal.
    """

    def __init__(self, cooldown: float, bullet_speed: float, muzzle_offset: float,
                 sprites: dict[tuple[int, int], pygame.Surface],
                 special: bool = False, special_spread: float = 0.0) -> None:
        self.special = special
        self.special_spread = special_spread
        self.cooldown = cooldown
        self.timer = 0.0  # segundos que faltan para poder volver a disparar
        self.bullet_speed = bullet_speed
        self.muzzle_offset = muzzle_offset
        self.sprites = sprites  # sprite de bala por dirección (dx, dy)
        self.held = False  # FIRE está presionada: dispara en cuanto termina el enfriamiento
        self.trigger = False  # pulsación pendiente: asegura el disparo aunque se suelte antes del frame
        self.special_held = False  # SPECIAL está presionada
        self.special_trigger = False  # pulsación pendiente de SPECIAL
