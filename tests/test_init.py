from pathlib import Path

from projectutils.init import Directory, File, Tree


def test_path_lookup(chtmp):
    """Confirm that complex structure is fully created."""
    files = [
        File("first.txt", "content"),
        File("second.txt", "content 2"),
        File("third.json", "[1,2,3]"),
    ]
    child = Directory("child", [files[1]])
    parent = Directory("parent", [child, files[0]])
    second_parent = Directory("second parent", [files[2]])
    tree = Tree([parent, second_parent])
    assert tree["parent"] is parent
    assert tree["parent/child/second.txt"] is files[1]
    assert tree["parent/child"] is child
    assert tree["second parent/third.json"] is files[2]

    _subdir = tree["parent/child"]
    assert isinstance(_subdir, Directory)
    assert _subdir["second.txt"] is files[1]


def test_random_dots_in_paths(chtmp):
    """Confirm that a path like ``parent/./file.txt`` evaluates to ``parent/file.txt``."""
    with chtmp() as path:
        tree = Tree(
            [
                Directory(
                    "parent",
                    [
                        Directory(".", [File("file.txt", "content")]),
                    ],
                ),
            ]
        )
        tree.create(path)
        assert Path(path, "parent").is_dir()
        assert Path(path, "parent/file.txt").is_file()
        assert Path(path, "parent/file.txt").read_text() == "content"


def test_creates_complex_structure(chtmp):
    """Confirm that complex structure is fully created."""
    with chtmp() as path:
        tree = Tree(
            [
                Directory(
                    "parent",
                    [
                        File("first.txt", "content"),
                        Directory("child", [File("second.txt", "content 2")]),
                    ],
                ),
                Directory("second parent", [File("third.json", "[1,2,3]")]),
            ]
        )
        tree.create(path)
        assert Path(path, "parent").is_dir()
        assert Path(path, "parent/first.txt").is_file()
        assert Path(path, "parent/first.txt").read_text() == "content"
        assert Path(path, "parent/child").is_dir()
        assert Path(path, "parent/child/second.txt").is_file()
        assert Path(path, "parent/child/second.txt").read_text() == "content 2"
        assert Path(path, "second parent").is_dir()
        assert Path(path, "second parent/third.json").is_file()
        assert Path(path, "second parent/third.json").read_text() == "[1,2,3]"
