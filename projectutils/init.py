from __future__ import annotations

import os

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from pathlib import Path


__all__ = [
    "Tree",
    "Directory",
    "File",
    "Node",
    "chdir",
]


class chdir(AbstractContextManager):
    """Non thread-safe context manager to change the current working directory.
    In the future replace with built-in version: https://github.com/python/cpython/pull/28271"""

    def __init__(self, path):
        self.path = path
        self._old_cwd = []

    def __enter__(self):
        self._old_cwd.append(os.getcwd())
        os.chdir(self.path)

    def __exit__(self, *excinfo):
        os.chdir(self._old_cwd.pop())


class Node(ABC):
    """Base class for nodes."""

    def __init__(self, path: str):
        self.path = Path(path)
        if "/" in str(self.path):
            raise ValueError("Path can't traverse nodes.")
        self.errors = []

    @abstractmethod
    def create(self):
        ...

    def __str__(self) -> str:
        return f"{self.path}"

    def __repr__(self):
        return f"<{self.__class__.__name__} '{self.path}'>"


class Directory(Node):
    """Node that represents a directory with childs.

    Creating a directory will recursively creat all childs."""

    def __init__(self, path: str, childs: list[Node] | None = None):
        super().__init__(path)
        self.childs = childs or []

    def create(self):
        self.path.mkdir(exist_ok=str(self.path) == ".")
        with chdir(self.path):
            for child in self.childs:
                child.create()

    def _get_direct_child_node(self, node, child_name):
        if child_name == ".":
            return node
        for child in node:
            if str(child.path) == child_name:
                return child

    def __getitem__(self, path: str) -> Node:
        """
        Allows child node lookup based on relative path.

        >>> file = File("file.txt", "content")
        >>> tree = Directory("parent", [Directory("child", [file])])
        >>> tree["."]
        <Directory 'parent'>
        >>> tree["child"]
        <Directory 'child'>
        >>> tree["child/file.txt"]
        <File 'file.txt'>
        >>> tree["child/file.txt"] is file
        True
        >>> tree["child/does_not_exists.txt"]
        Traceback (most recent call last):
            File "<stdin>", line 1, in <module>
        FileNotFoundError: Path not found
        """
        spaths = path.split("/")
        cur_node = self
        for spath in spaths[:-1]:
            cur_node = self._get_direct_child_node(cur_node, spath)
            if not isinstance(cur_node, Directory):
                raise FileNotFoundError("Path not found")
        cur_node = self._get_direct_child_node(cur_node, spaths[-1])
        if not cur_node:
            raise FileNotFoundError("Path not found")
        return cur_node

    def __iter__(self):
        return self.childs.__iter__()


class File(Node):
    """Node that represents a file with content.

    Additional `optional` and `warning` attributes may be passed to constructor.
    If `optional` is True (default) a :exc:`FileNotFoundError` will be rised if the file exists at creation time.
    If `optional` is False, only a `warning` (if any) will be printed to the screen.
    """

    def __init__(
        self,
        path: str,
        content: str,
        optional: bool = False,
        warning: str | None = None,
    ):
        super().__init__(path)
        self.content = content
        self.optional = optional
        self.warning = warning

    def create(self):
        if self.path.exists():
            if self.warning:
                self.warn()
            if self.optional:
                return
            raise FileExistsError(self.path)
        self.path.write_text(self.content)

    def warn(self):
        print(self.warning)


class Tree(Directory):
    def __init__(self, nodes: list[Node]):
        super().__init__(".", nodes)

    def create(self, directory: Path | str):
        """Recursively create whole tree."""
        with chdir(directory):
            super().create()
