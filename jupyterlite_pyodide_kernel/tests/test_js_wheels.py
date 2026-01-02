"""Validate the JS wheel metadata."""

import json
from jupyterlite_core.constants import UTF8
from .conftest import PYODIDE_KERNEL_EXTENSION

from jupyterlite_pyodide_kernel.constants import PYODIDE_PYTHON_VERSION
from jupyterlite_core.constants import ALL_JSON


def test_wheel_requires_python() -> None:
    """Verify the ``all.json`` agrees with the pyodide python version."""
    all_json = PYODIDE_KERNEL_EXTENSION / "static/pypi" / ALL_JSON
    expect_requires_python = f">={PYODIDE_PYTHON_VERSION}"
    for name, pkg_info in json.loads(all_json.read_text(**UTF8)).items():
        for version, wheel_infos in pkg_info["releases"].items():
            for wheel_info in wheel_infos:
                requires_python = wheel_info["requires_python"]
                msg = f"{name} {version} should require python {expect_requires_python}"
                assert expect_requires_python in requires_python, msg
