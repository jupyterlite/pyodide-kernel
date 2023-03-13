"""Use the demo site for a more extensive test."""
import json
import os
import shutil
from pathlib import Path

import pytest
from jupyterlite_core.constants import UTF8

from jupyterlite_pyodide_kernel.constants import PYPI_WHEELS

from .conftest import HERE

IN_TREE_EXAMPLES = HERE / "../../../examples"
EXAMPLES = Path(os.environ.get("LITE_PYODIDE_KERNEL_DEMO", IN_TREE_EXAMPLES))

if not EXAMPLES.exists():  # pragma: no cover
    pytest.skip(
        "not in a source checkout, skipping example test", allow_module_level=True
    )


@pytest.fixture
def an_example_with_tarball(tmp_path, a_pyodide_tarball):
    examples = tmp_path / EXAMPLES.name
    shutil.copytree(EXAMPLES, examples)
    config_path = examples / "jupyter_lite_config.json"
    config = json.loads(config_path.read_text(**UTF8))
    config["PyodideAddon"]["pyodide_url"] = str(a_pyodide_tarball)
    config_path.write_text(json.dumps(config))
    return examples


def test_examples_good(script_runner, an_example_with_tarball):
    """verify the demo site builds (if it available)"""
    opts = dict(cwd=str(an_example_with_tarball))

    build = script_runner.run("jupyter", "lite", "build", **opts)
    assert build.success

    archive = script_runner.run("jupyter", "lite", "archive", **opts)
    assert archive.success

    check = script_runner.run("jupyter", "lite", "check", **opts)
    assert check.success


def test_examples_bad_missing(script_runner, an_example_with_tarball):
    """verify the demo site check fails for missing deps"""
    opts = dict(cwd=str(an_example_with_tarball))

    shutil.rmtree(an_example_with_tarball / PYPI_WHEELS)

    check = script_runner.run("jupyter", "lite", "check", **opts)
    assert not check.success
    all_out = f"{check.stderr}{check.stdout}"
    assert "ipython" in all_out, "didn't find the missing dependent"
    assert "sqlite3" in all_out, "didn't find the missing dependency"
