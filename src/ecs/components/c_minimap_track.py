class CMinimapTrack:
    """Entidad visible en el minimapa. kind: player, base o formation."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
