"""tests of pyodide-lock customization"""

from __future__ import annotations

import json

from typing import TYPE_CHECKING
import pytest

if TYPE_CHECKING:
    from pytest_console_scripts import ScriptRunner
    from pathlib import Path


def test_pyodide_lock(
    an_empty_lite_dir: Path,
    script_runner: ScriptRunner,
    a_pyodide_tarball: str,
) -> None:
    """can we generate a custom pyodide-lock.json?"""
    HAS_PYODIDE_LOCK_UV = False
    try:
        from pyodide_lock.uv_pip_compile import _find_uv_path

        HAS_PYODIDE_LOCK_UV = _find_uv_path() is not None
    except ImportError as err:
        msg = f"can't test pyodide-lock without pyodide_lock and uv: {err}"
        pytest.skip(msg)

    pargs = ["--pyodide", a_pyodide_tarball]
    config = {"PyodideLockAddon": {"enabled": True}}

    kwargs = dict(cwd=str(an_empty_lite_dir))
    (an_empty_lite_dir / "jupyter_lite_config.json").write_text(json.dumps(config))

    status = script_runner.run(["jupyter", "lite", "status", *pargs], **kwargs)
    assert status.success, "status did NOT succeed"

    build = script_runner.run(["jupyter", "lite", "build", *pargs], **kwargs)
    assert build.success, "the build did NOT succeed"

    pyodide_path = an_empty_lite_dir / "_output/static/pyodide/pyodide.js"
    lock_path = an_empty_lite_dir / "_output/static/pyodide-lock/pyodide-lock.json"
    assert pyodide_path.exists(), "pyodide.js does not exist"
    assert lock_path.exists(), "pyodide-lock.json does not exit"

    check = script_runner.run(["jupyter", "lite", "check", *pargs], **kwargs)
    assert check.success, "the check did NOT succeed"
