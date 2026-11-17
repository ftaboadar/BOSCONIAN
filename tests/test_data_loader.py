"""Pruebas de los cargadores de datos (#53): lectura y validación de JSON."""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.getcwd())

from src.engine import data_loader
from src.engine.data_loader import (ConfigError, level_numbers, level_path, load_entity_cfg,
                                    load_json, load_level, load_resources, require_keys)


class TempCfg(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = self._tmp.name

    def write(self, name: str, data) -> str:
        path = os.path.join(self.dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))
        return path


class LoadJsonTests(TempCfg):
    def test_lee_un_json(self):
        self.assertEqual(load_json(self.write("a.json", {"x": 1})), {"x": 1})

    def test_archivo_inexistente(self):
        with self.assertRaisesRegex(ConfigError, "No existe"):
            load_json(os.path.join(self.dir, "no_esta.json"))

    def test_json_invalido(self):
        with self.assertRaisesRegex(ConfigError, "JSON inválido"):
            load_json(self.write("malo.json", "{ no es json"))


class RequireKeysTests(unittest.TestCase):
    def test_indica_las_claves_faltantes(self):
        with self.assertRaisesRegex(ConfigError, "faltan las claves b, c"):
            require_keys({"a": 1}, ("a", "b", "c"), "origen")

    def test_rechaza_lo_que_no_es_objeto(self):
        with self.assertRaisesRegex(ConfigError, "objeto JSON"):
            require_keys([1, 2], ("a",), "origen")


class LevelTests(TempCfg):
    LEVEL = {"round": 2, "player_start": {"x": 1, "y": 2},
             "bases": [{"x": 3, "y": 4, "orientation": "vertical"}]}

    def use_levels_dir(self):
        return mock.patch.object(data_loader, "LEVELS_DIR", os.path.join(self.dir, "levels"))

    def test_nombre_del_archivo_por_numero(self):
        self.assertTrue(level_path(3).endswith("level_03.json"))

    def test_carga_un_nivel_valido(self):
        self.write("levels/level_02.json", self.LEVEL)
        with self.use_levels_dir():
            self.assertEqual(load_level(2)["round"], 2)

    def test_nivel_inexistente(self):
        with self.use_levels_dir(), self.assertRaises(ConfigError):
            load_level(9)

    def test_nivel_sin_claves(self):
        self.write("levels/level_01.json", {"round": 1})
        with self.use_levels_dir(), self.assertRaisesRegex(ConfigError, "player_start, bases"):
            load_level(1)

    def test_orientacion_invalida(self):
        bad = dict(self.LEVEL, bases=[{"x": 0, "y": 0, "orientation": "diagonal"}])
        self.write("levels/level_01.json", bad)
        with self.use_levels_dir(), self.assertRaisesRegex(ConfigError, "orientation"):
            load_level(1)

    def test_lista_los_niveles_existentes_ordenados(self):
        for n in ("level_10.json", "level_02.json", "otro.json", "level_x.json"):
            self.write(f"levels/{n}", self.LEVEL)
        with self.use_levels_dir():
            self.assertEqual(level_numbers(), [2, 10])

    def test_sin_carpeta_de_niveles(self):
        with self.use_levels_dir():
            self.assertEqual(level_numbers(), [])

    def test_el_nivel_1_del_repo_es_valido(self):
        self.assertEqual(load_level(1)["round"], 1)


class EntityAndResourceTests(TempCfg):
    def test_entidad_con_claves_requeridas(self):
        self.write("enemies.json", {"speed": 10})
        with mock.patch.object(data_loader, "CFG_DIR", self.dir):
            self.assertEqual(load_entity_cfg("enemies", ("speed",)), {"speed": 10})
            with self.assertRaisesRegex(ConfigError, "points"):
                load_entity_cfg("enemies", ("speed", "points"))

    def test_resources_con_seccion_mal_formada(self):
        path = self.write("resources.json", {"images": ["a.png"]})
        with self.assertRaisesRegex(ConfigError, "images"):
            load_resources(path)

    def test_resources_del_repo(self):
        self.assertIn("fonts", load_resources())


if __name__ == "__main__":
    unittest.main()
