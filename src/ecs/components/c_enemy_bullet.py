class CEnemyBullet:
    """Bala de una torreta. Desaparece al acabarse su tiempo o al chocar."""

    def __init__(self, seconds_left: float) -> None:
        self.seconds_left = seconds_left
