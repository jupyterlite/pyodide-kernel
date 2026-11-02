"""Validate the integrity of the repo (or source checkout)"""

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jupyterlite_core.constants import UTF8

from jupyterlite_pyodide_kernel import __version__
from jupyterlite_pyodide_kernel.constants import PYODIDE_VERSION

from .conftest import ROOT

GH = ROOT / ".github"
DEPENDABOT = GH / "dependabot.yml"

PACKAGES = ROOT / "packages"
KERNEL_PKG = PACKAGES / "pyodide-kernel"
KERNEL_PKG_JSON = KERNEL_PKG / "package.json"

if not KERNEL_PKG_JSON.exists():  # pragma: no cover
    pytest.skip(
        "not in a source checkout, skipping repo tests", allow_module_level=True
    )


def test_pyodide_version():
    kernel_pkg_data = json.loads(KERNEL_PKG_JSON.read_text(**UTF8))
    assert kernel_pkg_data["devDependencies"]["pyodide"] == PYODIDE_VERSION, (
        f"{kernel_pkg_data} pyodide devDependency is not {PYODIDE_VERSION}"
    )


def test_dependabot_branches(the_production_x_branch: str) -> None:
    db_yaml = {**yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))}
    updates: list[dict[str, Any]] = db_yaml["updates"]
    main = "main"
    branch_path_ecosystems = {
        (
            u.get("target-branch", main),
            str(u["directory"]),
            str(u["package-ecosystem"]),
        ): u
        for u in updates
    }

    missing: list[tuple[str, str, str]] = []

    for (branch, path, ecosystem), update in branch_path_ecosystems.items():
        if branch != main:
            continue
        expect_x = (the_production_x_branch, path, ecosystem)
        if expect_x not in branch_path_ecosystems:
            missing += [expect_x]

    assert not missing, (
        f"update dependabot.yml for {the_production_x_branch}: {missing}"
    )


# fixtures
@pytest.fixture
def the_default_pyodide_url():
    return f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/pyodide.mjs"


@pytest.mark.parametrize(
    "pkg_path",
    [
        "pyodide-kernel-extension/schema/kernel.v0.schema.json",
        "pyodide-kernel-extension/src/index.ts",
    ],
)
def test_pyodide_url(pkg_path: Path, the_default_pyodide_url: str):
    assert the_default_pyodide_url in (PACKAGES / pkg_path).read_text(**UTF8)


@pytest.fixture
def the_production_x_branch() -> str:
    major, minor, patch = __version__.split(".")
    assert major == "0", "revisit branch support strategy for 1.x"
    x_bits = []
    if any(pre in patch for pre in ("a", "b", "rc")):
        x_bits = [major, str(int(minor) - 1)]
    else:
        x_bits = [major, minor]
    return ".".join([*x_bits, "x"])
