# Cosmonian

Recreación del arcade Bosconian (Sharp X68000) hecha con **Pygame (pygame-ce)** y **Esper** (ECS) para la materia Introducción al Desarrollo de Videojuegos.

Resolución nativa 256x208, escalada a la ventana.

## Estado

El proyecto avanza por hitos (ver el tablero del repositorio).

| Hito | Contenido | Estado |
|---|---|---|
| 1 Base | ECS, game loop, service locator, escenas, command, configuración JSON | Hecho |
| 2 Mundo | Estrellas, parallax, cámara, wraparound, minimapa | Hecho |
| 3 Jugador | Aceleración, disparo, colisiones, vidas, puntaje | Pendiente |
| 4 Enemigos y bases | IA, bases, obstáculos, alertas | Pendiente |
| 5 Flujo completo | Menús, 10 niveles, sonidos, victoria y derrota, modo trampa | En curso |
| 6 Bonos | Intro, atractor, cutscene, gamepad, jefe, formaciones, espía, editor | En curso |
| 7 Entrega | Publicación, documentos y video | Pendiente |

Lo que ya se puede ver: menú del título (jugar, elegir nivel, instrucciones, créditos), modo atractor tras 15 s sin tocar nada, escena de nivel con "BLAST OFF!", pausa con P ("JUEGO PAUSADO") y un jugador y unas bases provisionales sobre un mundo toroidal con cámara y minimapa.

## Requisitos y ejecución

```
python -m venv .venv
source .venv/bin/activate      # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Controles

| Tecla | Acción |
|---|---|
| Flechas | Cambiar la dirección de la nave; navegar el menú |
| Izquierda / Derecha | En el menú, sobre NIVEL: cambiar de nivel |
| Z | Disparar (adelante y atrás) |
| X | Habilidad especial |
| P | Pausar / reanudar el nivel |
| Enter | Elegir una opción del menú; en pausa, pide confirmar la salida al título |
| Esc | Volver desde instrucciones y créditos; en el nivel (jugando o en pausa), pide confirmar la salida al título (Enter: sí, Esc: no) |
| F1 | Modo trampa |

Las teclas se definen en `assets/cfg/input.json`; no hace falta tocar el código para cambiarlas. El gamepad es un bono y aún no está implementado.

Disparo y habilidad especial se activan al completarse el hito 3. Por ahora la pausa vuelve al título con Enter; cuando esté el menú de opciones se enlazará desde ahí (#30).

## Modo trampa

La tecla F1 queda reservada para el modo trampa, que permitirá recorrer el juego sin morir. **Todavía no está implementado** (tarea #34); cuando lo esté, aquí se documenta qué hace exactamente.

## Arquitectura

```
main.py                  punto de entrada
assets/cfg/              toda la configuración en JSON (ventana, mundo, input, menú, recursos, niveles)
src/ecs/components/      componentes: solo datos
src/ecs/systems/         sistemas: lógica que recorre componentes
src/create/              ensamblado de entidades a partir de componentes
src/engine/              motor, escenas, input, menú, service locator y cargadores de datos
tests/                   pruebas con unittest
```

Patrones usados:
- **ECS** con Esper: cada escena tiene su propio mundo.
- **Game loop** a framerate fijo en `GameEngine`.
- **Command** simplificado: tecla física → acción lógica, según `input.json`.
- **Service locator**: acceso único a imágenes, sonidos, música y fuentes.
- **Escena**: título, instrucciones, créditos, nivel y modo atractor.
- **Archivos de configuración**: leídos y validados por `src/engine/data_loader.py`.
- **State**: pendiente, llega con la IA de los enemigos (tarea #20).

## Pruebas

```
python -m unittest discover -s tests -p "test_*.py"
python tests/smoke_test.py
```

## Créditos y licencias

- Imágenes: Diana Pacheco (CC-BY-4.0).
- Música: Centurion of War (CC0).
- Fuente Press Start 2P: CodeMan38 (SIL Open Font License 1.1).

El detalle está en `assets/LICENCIAS.txt`.

## Equipo

Cuentas de GitHub: ftaboadar, jdbu2002, jzarruke, santi8194.
