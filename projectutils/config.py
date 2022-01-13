"""
This module provides a structure for a configurable application.
You can create a customized :class:`Config` object passing any :class:`ConfigSource`
you need (like :class:`JSONSource` and :class:`ENVSource`) and a config schema.

Here's an example of a simple app that uses this module:

``schema.json``:

.. code:: json

    {
        "string": {"doc": "String config", "format": "string", "default": "DEFAULT"},
        "integer": {"doc": "Integer config", "format": "int", "default": 1},
        "float": {"doc": "Float config", "format": "float", "default": 1.1},
        "list": {"doc": "List config", "format": "list", "default": ["a", "b", "c"]},
        "bool": {"doc": "Bool config", "format": "bool", "default": true},
        "nested.string": {"doc": "String config", "format": "string", "default": "DEFAULT"},
    }


``/etc/myapp/config.json``:

.. code:: json

    {
        "float": 2.2,
        "string": "loaded from json",
        "nested": {
            "string": "loaded from json"
        }
    }



``/etc/myapp/.env``:

.. code:: bash

    MYAPP_CONF_LIST="e,n,v"
    MYAPP_CONF_BOOL="False"
    MYAPP_CONF_NESTED_STRING="loaded from env"


``app.py``:

.. code:: python

    import json
    from pathlib import Path
    from projectutils.config import Config, ENVSource, JSONSource


    # Setup includes loading the schema
    # and defining some params used in sources.
    with open("schema.json", "r") as fp:
        schema = json.load(fp)

    envs_prefix = "MYAPP_CONF_"
    configs_root = Path("/etc/myapp")

    # Source definition dictates precedence.
    # In this case ENV values will override JSON values.
    sources = [
        JSONSource(configs_root / "config.json"),
        ENVSource(envs_prefix, configs_root),
    ]

    # Load config
    config = Config(schema, sources)


    config.get("integer")
    # 1

    config.get("float")
    # 2.2

    config.get("bool")
    # False

    config.get("list")
    # ['e', 'n', 'v']

    config.get("nested.string")
    # 'loaded from env'

    config.get("string")
    # 'loaded from json'

    config.get("nested")
    # {'nested': 'loaded from env'}


"""
from __future__ import annotations

import os
import json
import difflib

from abc import ABC, abstractmethod
from typing import Generic, Any, Iterable, TypeAlias, TypeVar
from pathlib import Path

import rst
from dotenv import load_dotenv


__all__ = [
    "Config",
    "ConfigSchema",
    "ConfigSource",
    "ConfigDef",
    "FORMATTERS",
    "JSONSource",
    "ENVSource",
    "LCDict",
    "flatten",
    "closest_formatter",
    "get_formatter",
    "InvalidConfigValue",
    "ConfigNotDefined",
    "AcceptedTypes",
]


_KT = TypeVar("_KT", bound=str)
_VT = TypeVar("_VT")


AcceptedTypes: TypeAlias = int | float | str | bool | list


class LCDict(dict, Generic[_KT, _VT]):
    """Lowercase dictionary for case-insensitive config names."""

    def __setitem__(self, key: _KT, value: _VT) -> None:
        return super().__setitem__(key.lower(), value)

    def __getitem__(self, key: _KT):
        return super().__getitem__(key.lower())

    def __contains__(self, key: _KT):
        return key.lower() in self.keys()


def flatten(dict_: dict, base_path: str = "") -> dict:
    """Flattens a multi dimensional mapping into a 1-dimensional dict.

    >>> flatten({"a": {"b": {"c": 1}, "d": 2}, "e": 3})
    {'a.b.c': 1, 'a.d': 2, 'e': 3}
    """
    out = {}
    for key, value in dict_.items():
        cur_path = base_path + "." + key
        cur_path = cur_path.strip(".")
        if isinstance(value, dict):
            out |= flatten(value, cur_path)
        else:
            out[cur_path] = value
    return out


class ConfigSource(ABC):
    """Base class for config sources.

    All ConfigSource's must implement `_load_data()` returning a
    1-dimensional mapping of `path: value`."""

    def __init__(self):
        self.data = self._load_data()

    def items(self):
        return self.data.items()

    @abstractmethod
    def _load_data(self) -> dict[str, Any]:
        """Must return a dict of `path: value` mappings."""
        pass


class JSONSource(ConfigSource):
    """Loads configs from a JSON file.

    The JSON data does not need to be flat.
    For example,

    .. code:: json

        {"parent": {"child": "value"}}

    is the same as

    .. code:: json

        {"parent.child": "value"}

    """

    def __init__(self, file: Path):
        self.file = file
        super().__init__()

    def _load_data(self) -> dict[str, Any]:
        if not self.file.is_file():
            return {}
        with self.file.open("r") as fp:
            data = json.load(fp)
        return flatten(data)


class ENVSource(ConfigSource):
    """Loads configs from environment variables.

    Also loads envvars from ``.env`` files in `root`.

    Always tries to load ``.env``. Additionally tries to loads ``.env.{name}`` files
    for all names in `envs`.

    Only environment variables that start with `prefix` will be loaded."""

    def __init__(self, prefix: str, root: Path, envs: list[str] = None):
        self.prefix = prefix
        self.root = root
        self.envs = set(envs or [])
        self.base_envfile = root / ".env"
        super().__init__()

    def _load_data(self) -> dict[str, Any]:
        if self.base_envfile.is_file():
            load_dotenv(self.base_envfile)
        for env in self.envs:
            envfile = self.root / f".env.{env}"
            if not envfile.is_file():
                raise FileNotFoundError(str(envfile))
            load_dotenv(envfile, override=True)
        return self._parse_environ()

    def _parse_environ(self) -> dict:
        output = {}
        for name, value in os.environ.items():
            if name.startswith(self.prefix):
                cname = self._get_config_name(name)
                output[cname] = value
        return output

    def _get_config_name(self, name: str) -> str:
        name = name.replace(self.prefix, "")
        return name.replace("_", ".")


def _list_formatter(value):
    if isinstance(value, str):
        return value.split(",")
    elif isinstance(value, list):
        return value
    raise InvalidConfigValue("Invalid value for list.")


def _bool_formatter(value):
    if isinstance(value, str):
        value = value.lower()
        if value in ("1", "0", "true", "false"):
            return value in ("1", "true")
        raise InvalidConfigValue(
            "Invalid value for bool. Accepted string values are: 1, 0, true, false"
        )
    return bool(value)


#: All available formaters.
FORMATTERS = {
    "int": int,
    "string": str,
    "float": float,
    "bool": _bool_formatter,
    "list": _list_formatter,
}


def closest_formatter(format: str):
    """Returns a formatter recommendation for error messages."""
    out = 0, None
    for option in FORMATTERS.keys():
        ratio = difflib.SequenceMatcher(None, format, option).ratio()
        if ratio > out[0]:
            out = ratio, option
    return out[1]


def get_formatter(format: str):
    """Returns a formatter given it's name."""
    if format in FORMATTERS.keys():
        return FORMATTERS[format]
    closest = closest_formatter(format)
    hint = f" Did you mean '{closest}'?" if closest else ""
    raise ValueError(f"Invalid config formatter: '{format}'.{hint}")


class ConfigDef:
    """Stores Config Definition attributes for the :class:`ConfigSchema`."""

    def __init__(self, path: str, doc: str, format: str, default: Any):
        self.path = path
        self.doc = doc
        self.format = format
        self.formatter = get_formatter(format)
        self.default = default


class ConfigSchema:
    """Stores all available configs and their attributes (as :class:`ConfigDef` s)."""

    def __init__(self, data: dict):
        self.schema: LCDict[str, ConfigDef] = self._load(data)

    def __getitem__(self, path: str) -> Any:
        if path in self.schema:
            return self.schema[path]
        raise ConfigNotDefined(f"'{path}' not defined in the config schema.")

    @classmethod
    def from_json_file(cls, file: str | Path) -> ConfigSchema:
        data = json.loads(Path(file).read_text())
        return ConfigSchema(data)

    def _load(self, data: dict) -> LCDict[str, ConfigDef]:
        output = LCDict()
        for path, definition in data.items():
            output[path] = ConfigDef(path=path, **definition)
        return output

    def keys(self) -> Iterable[str]:
        """Returns all config names."""
        return self.schema.keys()

    def items(self) -> Iterable[tuple[str, ConfigDef]]:
        """Returns iterable of all configs in the schema."""
        return self.schema.items()

    def defaults(self) -> dict:
        """Returns deep tree of default configs."""
        defaults = {}
        for path, def_ in self.items():
            _add_path_to_tree(defaults, path, def_.default)
        return defaults


def _add_path_to_tree(tree: dict, path: str, value: Any):
    """Adds a dot concatenated path and its value to a deep tree.

    >>> (d := _add_path_to_tree({}, "nested.first", 1))
    {'nested': {'first': 1}}
    >>> (d := _add_path_to_tree(d, "nested.second", 2))
    {'nested': {'first': 1, 'second': 2}}
    >>> (d := _add_path_to_tree(d, "nested.deep.first", "value"))
    {'nested': {'first': 1, 'second': 2, 'deep': {'first': 'value'}}}
    >>> (d := _add_path_to_tree(d, "top", True))
    {'nested': {'first': 1, 'second': 2, 'deep': {'first': 'value'}}, 'top': True}
    >>> (d := _add_path_to_tree(d, "top", False))
    {'nested': {'first': 1, 'second': 2, 'deep': {'first': 'value'}}, 'top': False}
    """
    curnode = tree
    parts = path.split(".")
    for part in parts[:-1]:
        curnode = curnode.setdefault(part, {})
    curnode[parts[-1]] = value
    return tree


class Config:
    """Readonly config interface. Loads and merges config data from multiple sources."""

    def __init__(self, schema: ConfigSchema, sources: list[ConfigSource] | None = None):
        self.sources = sources or []
        self.schema = schema
        self.data: LCDict[str, AcceptedTypes] = self._merge_sources_and_format()

    def get(self, path: str) -> AcceptedTypes | dict:
        """Returns value for config `path` looking at, in order:

            - Data loaded from sources
            - Schema defaults

        If `path` is not an exact match (e.g `a.b` when `a.b.c` and `a.b.d` exists)
        a deep tree containing all child values will be returned.

        NameError is raised if `path` is not found.
        """
        path = path.lower()
        if path in self.data.keys():
            return self.data[path]
        if path in self.schema.keys():
            return self.schema[path].default
        if any(name.startswith(path) and name != path for name in self.schema.keys()):
            return self._get_tree(path)
        raise NameError(path)

    def _get_tree(self, path_prefix: str) -> dict:
        """Builds a deep tree with all configs that start with `path_prefix`."""
        tree = {}
        for name, def_ in self.schema.items():
            if name.startswith(path_prefix):
                value = self.data.get(name, def_.default)
                subpath = name[len(path_prefix) + 1 :]  # +1 accounts for last '.'
                tree = _add_path_to_tree(tree, subpath, value)
        return tree

    def _merge_sources_and_format(self) -> LCDict[str, AcceptedTypes]:
        """Merges configs loaded from multiple ConfigSources into a single,
        flat :class:`LCDict`. Values are formatted at this point."""
        data = LCDict()
        for config in self.sources:
            for path, value in config.items():
                formatted = self.schema[path].formatter(value)
                data[path.lower()] = formatted
        return data


def generate_docs(schema: ConfigSchema) -> str:
    """Generate RST text that documents `schema`.

    >>> data = {"app.email": {"doc": "some help", "format": "string", "default": ""},\
                "app.user": {"doc": "other help", "format": "string", "default": "admin"}}
    >>> schema = ConfigSchema(data)
    >>> print(generate_docs(schema))
    ========================
    Available configurations
    ========================
    <BLANKLINE>
    .. list-table:: All Configs
        :header-rows: 1
    <BLANKLINE>
        * -  Path
          -  Format
          -  Default
          -  Help
        * -  app.email
          -  string
          -  ``''``
          -  some help
        * -  app.user
          -  string
          -  admin
          -  other help
    <BLANKLINE>
    <BLANKLINE>
    All Defaults
    ############
    <BLANKLINE>
    .. code-block:: json
    <BLANKLINE>
        {
            "app": {
                "email": "",
                "user": "admin"
            }
        }
    <BLANKLINE>
    """
    doc = rst.Document("Available configurations")
    tbl = rst.Table("All Configs", ["Path", "Format", "Default", "Help"])
    for _, data in schema.items():
        tbl.add_item((data.path, data.format, data.default or "``''``", data.doc))
    doc.add_child(tbl)
    out = doc.get_rst()
    out += "\n\nAll Defaults\n############\n\n"
    out += ".. code-block:: json\n\n"
    defaults = json.dumps(schema.defaults(), indent=4)
    out += "\n".join(f"    {line}" for line in defaults.split("\n"))
    out += "\n"
    return out


class InvalidConfigValue(ValueError):
    pass


class ConfigNotDefined(ValueError):
    pass
