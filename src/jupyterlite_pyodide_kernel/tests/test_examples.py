"""Use the demo site for a more extensive test."""
import pytest
import shutil
import os
from pathlib import Path

from .conftest import HERE

IN_TREE_EXAMPLES = HERE / "../../../examples"
EXAMPLES = Path(os.environ.get("LITE_PYODIDE_KERNEL_DEMO", IN_TREE_EXAMPLES))

if not EXAMPLES.exists():  # pragma: no cover
    pytest.skip(
        "not in a source checkout, skipping example test", allow_module_level=True
    )


def test_examples(script_runner, tmp_path):
    """verity the demo site builds (if it available)"""
    examples = tmp_path / EXAMPLES.name
    shutil.copytree(EXAMPLES, examples)

    build = script_runner.run("jupyter", "lite", "build", cwd=str(examples))
    assert build.success

    build = script_runner.run("jupyter", "lite", "archive", cwd=str(examples))
    assert build.success

    build = script_runner.run("jupyter", "lite", "check", cwd=str(examples))
    assert build.success
