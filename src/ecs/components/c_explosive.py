class CExplosive:
    """La entidad explota al ser destruida. kind es un tipo de explosions.json."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
