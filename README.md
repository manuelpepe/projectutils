# projectutils

[![Documentation Status](https://readthedocs.org/projects/projectutils/badge/?version=latest)](https://projectutils.readthedocs.io/en/latest/?badge=latest)
[![Unit Tests](https://github.com/manuelpepe/projectutils/actions/workflows/tests.yml/badge.svg)](https://github.com/manuelpepe/projectutils/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/manuelpepe/projectutils/branch/main/graph/badge.svg?token=6Hjb772RWB)](https://codecov.io/gh/manuelpepe/projectutils)


A small collections of modular components useful in other projects.



## projectutils.init

The `init` module is helpful when you need to create a complex directory structure.
You can create objects that represent Directories and Files to create a tree.


```python
from pathlib import Path
from projectutils.init import Tree, Directory, File


tree = Tree([
    Directory("dir1"),
    Directory("dir2", [
        File("file.txt", "file content")
    ])
])

tree.create(Path("~/project").expanduser())

# $ tree ~/project
# ~/project
# ├── dir1
# └── dir2
#     └── file.txt
```


## projectutils.config

The `config` module allows you to define a configuration schema and dinamically load configurations
from multiple sources.

`schema.json`:

```json
{
    "string": {"doc": "String config", "format": "string", "default": "DEFAULT"},
    "integer": {"doc": "Integer config", "format": "int", "default": 1},
    "float": {"doc": "Float config", "format": "float", "default": 1.1},
    "list": {"doc": "List config", "format": "list", "default": ["a", "b", "c"]},
    "bool": {"doc": "Bool config", "format": "bool", "default": true},
    "nested.string": {"doc": "String config", "format": "string", "default": "DEFAULT"},
}
```

`/etc/myapp/config.json`:
```json
{
    "float": 2.2,
    "string": "loaded from json",
    "nested": {
        "string": "loaded from json"
    }
}
```


`/etc/myapp/.env`:
```bash
MYAPP_CONF_LIST="e,n,v"
MYAPP_CONF_BOOL="False"
MYAPP_CONF_NESTED_STRING="loaded from env"

```

`app.py`:

```python
import json
from pathlib import Path
from projectutils.config import Config, ENVSource, JSONSource, ConfigSchema


# Load schema
schema = ConfigSchema.from_json_file("schema.json")

# Define Sources
envs_prefix = "MYAPP_CONF_"
configs_root = Path("/etc/myapp")
sources = [
    JSONSource(configs_root / "config.json"),
    ENVSource(envs_prefix, configs_root),
]
# Source definition dictates precedence.
# In this case ENV values will override JSON values.

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
```
