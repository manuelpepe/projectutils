import os

from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import contextmanager

import pytest

from projectutils.init import chdir


@pytest.fixture
def chtmp():
    @contextmanager
    def _chtmp():
        prev_environ = os.environ.copy()
        with TemporaryDirectory() as tmp:
            with chdir(tmp):
                yield Path(tmp)
        os.environ.clear()
        os.environ.update(prev_environ)

    return _chtmp
