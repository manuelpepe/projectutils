import json

from pathlib import Path
from collections import namedtuple

import pytest

from projectutils.config import Config, ENVSource, JSONSource


SCHEMA = {
    "string": {"doc": "String config", "format": "string", "default": "DEFAULT"},
    "integer": {"doc": "Integer config", "format": "int", "default": 1},
    "float": {"doc": "Float config", "format": "float", "default": 1.1},
    "list": {"doc": "List config", "format": "list", "default": ["a", "b", "c"]},
    "bool": {"doc": "Bool config", "format": "bool", "default": True},
    "nested.config": {"doc": "nested", "format": "string", "default": ""},
    "deeply.nested.config": {"doc": "deeply nested", "format": "string", "default": ""},
    "deeply.nested.configtwo": {
        "doc": "deeply nested with multiple values",
        "format": "string",
        "default": "",
    },
}

RawExpected = namedtuple("RawExpected", "raw expected")

VALUES_FOR_ENV = {
    "string": RawExpected("env value", "env value"),
    "integer": RawExpected("123", 123),
    "float": RawExpected("2.2", 2.2),
    "list": RawExpected("d,e,f", ["d", "e", "f"]),
    "bool": RawExpected("False", False),
    "nested.config": RawExpected(
        "env value",
        "env value",
    ),
    "deeply.nested.config": RawExpected(
        "env value",
        "env value",
    ),
    "deeply.nested.configtwo": RawExpected(
        "env value",
        "env value",
    ),
}


VALUES_FOR_JSON = {
    "string": "json value",
    "integer": 123,
    "float": 2.2,
    "list": ["g", "h", "i"],
    "bool": False,
    "deeply": {"nested": {"config": "json value 3", "configtwo": "json value 4"}},
    "nested": {"config": "json value 2"},
}


EXPECTED_FOR_JSON = {
    "string": "json value",
    "integer": 123,
    "float": 2.2,
    "list": ["g", "h", "i"],
    "bool": False,
    "nested.config": "json value 2",
    "deeply.nested.config": "json value 3",
    "deeply.nested.configtwo": "json value 4",
}


@pytest.mark.parametrize("config", SCHEMA.items())
def test_config_without_sources(config):
    key, data = config
    cfg = Config(SCHEMA)
    assert cfg.get(key) == data["default"]


@pytest.mark.parametrize("config", VALUES_FOR_ENV.items())
def test_single_env_source(chtmp, config):
    def _as_env(name):
        return f'{prefix}{name.upper().replace("_", ".")}'

    prefix = "TEST_CONF_"
    key, data = config
    env_data = "\n".join(f'{_as_env(k)}="{v.raw}"' for k, v in VALUES_FOR_ENV.items())
    with chtmp() as cwd:
        envfile: Path = cwd / ".env"
        envfile.write_text(env_data + "\n")
        cfg = Config(SCHEMA, [ENVSource(prefix, cwd)])
        assert cfg.get(key) == data.expected


@pytest.mark.parametrize("config", EXPECTED_FOR_JSON.items())
def test_single_json_source(chtmp, config):
    key, expected = config
    with chtmp() as cwd:
        configfile: Path = cwd / "config.json"
        configfile.write_text(json.dumps(VALUES_FOR_JSON))
        cfg = Config(SCHEMA, [JSONSource(configfile)])
        assert cfg.get(key) == expected
