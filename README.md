# projectutils

A small collections of modular components useful in other projects.



## projectutils.init

The `init` module is helpful when you need to create a complex directory structure.
You can create objects that represent Directories and Files to create a tree.


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
}
```

`app.py`:

```python
from projectutils.config import Config, ENVSource


with open("schema.json", "r") as fp:
    schema = json.load(fp)
config = Config(schema)
```
