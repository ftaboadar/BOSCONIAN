"""Punto de entrada de BOSCONIAN (escritorio y web).

El bucle es asíncrono para que la versión web (pygbag) pueda ceder el control al navegador
en cada fotograma; en escritorio se comporta igual que un bucle normal.
"""
# Dependencias que pygbag instala en el navegador. Esper no va aquí: la versión web lleva
# su propia copia de esper 2.5 (ver tools/build_web.py).
# /// script
# dependencies = [
#     "pygame-ce",
# ]
# ///

import asyncio

from src.engine.game_engine import GameEngine


async def main() -> None:
    await GameEngine().run_async()


if __name__ == "__main__":
    asyncio.run(main())
