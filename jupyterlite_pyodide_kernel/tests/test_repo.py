"""Validate the integrity of the repo (or source checkout)"""

import json
from pathlib import Path


import pytest
from jupyterlite_core.constants import UTF8

from jupyterlite_pyodide_kernel.constants import PYODIDE_VERSION, PYODIDE_PYTHON_VERSION

from .conftest import HERE

PACKAGES = HERE / "../../packages"
KERNEL_PKG = PACKAGES / "pyodide-kernel"
KERNEL_PKG_JSON = KERNEL_PKG / "package.json"

if not KERNEL_PKG_JSON.exists():  # pragma: no cover
    pytest.skip(
        "not in a source checkout, skipping repo tests", allow_module_level=True
    )

KERNEL_PKG_PY = KERNEL_PKG / "py"
PYPROJECTS = sorted(KERNEL_PKG_PY.glob("*/pyproject.toml"))


def test_pyodide_version():
    kernel_pkg_data = json.loads(KERNEL_PKG_JSON.read_text(**UTF8))
    assert kernel_pkg_data["devDependencies"]["pyodide"] == PYODIDE_VERSION, (
        f"{kernel_pkg_data} pyodide devDependency is not {PYODIDE_VERSION}"
    )


@pytest.fixture
def the_default_pyodide_url():
    return f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.js"


@pytest.mark.parametrize(
    "pkg_path",
    [
        "pyodide-kernel-extension/schema/kernel.v0.schema.json",
        "pyodide-kernel-extension/src/index.ts",
    ],
)
def test_pyodide_url(pkg_path: Path, the_default_pyodide_url: str):
    assert the_default_pyodide_url in (PACKAGES / pkg_path).read_text(**UTF8)


@pytest.mark.parametrize("pkg", sorted(p.parent.name for p in PYPROJECTS))
def test_wheel_requires_python(pkg: str) -> None:
    py_proj = KERNEL_PKG_PY / pkg / "pyproject.toml"
    assert f"""requires-python = ">={PYODIDE_PYTHON_VERSION}""" in py_proj.read_text(
        **UTF8
    )
