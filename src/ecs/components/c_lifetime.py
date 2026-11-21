class CLifetime:
    """Segundos que le quedan a la entidad antes de destruirse."""

    def __init__(self, remaining: float) -> None:
        self.remaining = remaining
