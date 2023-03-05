"""test configuration for jupyterlite-pyodide-kernel"""
import pytest
from pathlib import Path

from jupyterlite.tests.conftest import (
    an_empty_lite_dir,
    a_fixture_server,
    an_unused_port,
)

from jupyterlite_pyodide_kernel.constants import PYODIDE_VERSION

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"

WHEELS = [*FIXTURES.glob("*.whl")]

PYODIDE_GH = "https://github.com/pyodide/pyodide/releases/download"
PYODIDE_TARBALL = f"pyodide-core-{PYODIDE_VERSION}.tar.bz2"
PYODIDE_URL = f"{PYODIDE_GH}/{PYODIDE_VERSION}/{PYODIDE_TARBALL}"
PYODIDE_FIXTURE = FIXTURES / f".pyodide" / PYODIDE_VERSION / PYODIDE_TARBALL


@pytest.fixture
def index_cmd():
    """get the command line arguments for indexing a folder."""
    return ("jupyter", "piplite", "index")


@pytest.fixture
def a_pyodide_tarball():
    """maybe fetch the pyodide archive"""
    if not PYODIDE_FIXTURE.exists():  # pragma: no cover
        import shutil
        import urllib.request

        PYODIDE_FIXTURE.parent.mkdir(exist_ok=True, parents=True)
        with urllib.request.urlopen(PYODIDE_URL) as response:
            with PYODIDE_FIXTURE.open("wb") as fd:
                shutil.copyfileobj(response, fd)

    unpacked = PYODIDE_FIXTURE.parent / "pyodide/pyodide"

    if not unpacked.is_dir():  # pragma: no cover
        from jupyterlite.manager import LiteManager
        from jupyterlite.addons.base import BaseAddon

        manager = LiteManager()
        BaseAddon(manager=manager).extract_one(PYODIDE_FIXTURE, unpacked.parent)

    return PYODIDE_FIXTURE


@pytest.fixture
def a_pyodide_server(an_unused_port, a_pyodide_tarball):  # pragma: no cover
    """serve up the pyodide archive"""
    import subprocess

    root = a_pyodide_tarball.parent

    p = subprocess.Popen(
        ["python", "-m", "http.server", "-b", "127.0.0.1", f"{an_unused_port}"],
        cwd=str(root),
    )
    url = f"http://localhost:{an_unused_port}"
    yield url
    p.terminate()
