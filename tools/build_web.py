"""Arma la versión web del juego (pygbag) lista para subir a itch.io.

Uso, desde la raíz del proyecto y con las dependencias de requirements.txt instaladas:

    python tools/build_web.py

Deja el juego en dist/web/ (index.html y sus archivos) y el paquete dist/cosmonian-web.zip,
que es el que se sube a itch.io como proyecto HTML. Para probarlo antes en el navegador:

    python -m http.server --directory dist/web 8000     ->  http://localhost:8000

Se empaqueta una copia limpia (main.py, src y assets), no la carpeta del proyecto, para que
no viajen las pruebas, los documentos ni el entorno virtual. Esper va dentro de la copia:
pygbag solo instala en el navegador la última versión de cada paquete y el juego usa la
API de esper 2.5 (la de requirements.txt).
"""

import os
import shutil
import subprocess
import sys

import esper

NAME = "cosmonian"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.path.join(ROOT, "build", "web_src", NAME)
DIST = os.path.join(ROOT, "dist")
SOURCES = ("main.py", "src", "assets")
NO_CACHE = shutil.ignore_patterns("__pycache__", "*.pyc")


def main() -> None:
    if getattr(esper, "version", "") != "2.5":
        sys.exit(f"Se necesita esper 2.5 (hay {getattr(esper, 'version', '?')}): "
                 "pip install -r requirements.txt")
    shutil.rmtree(os.path.dirname(STAGE), ignore_errors=True)
    os.makedirs(STAGE)
    for name in SOURCES:
        src = os.path.join(ROOT, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(STAGE, name), ignore=NO_CACHE)
        else:
            shutil.copy(src, STAGE)
    shutil.copytree(os.path.dirname(esper.__file__), os.path.join(STAGE, "esper"), ignore=NO_CACHE)

    subprocess.run([sys.executable, "-m", "pygbag", "--build", STAGE], check=True)

    web = os.path.join(DIST, "web")
    shutil.rmtree(web, ignore_errors=True)
    shutil.copytree(os.path.join(STAGE, "build", "web"), web)
    archive = shutil.make_archive(os.path.join(DIST, f"{NAME}-web"), "zip", web)
    print(f"\nListo: {web}\nPara itch.io: {archive}")


if __name__ == "__main__":
    main()
