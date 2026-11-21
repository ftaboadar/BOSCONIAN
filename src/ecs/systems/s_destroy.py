import esper

from src.ecs.components.c_destroy import CDestroy


def system_destroy(world: esper.World) -> None:
    """Elimina las entidades marcadas con CDestroy.

    Se borran de inmediato porque las escenas no llaman a world.process().
    """
    for ent in [ent for ent, _ in world.get_component(CDestroy)]:
        world.delete_entity(ent, immediate=True)
