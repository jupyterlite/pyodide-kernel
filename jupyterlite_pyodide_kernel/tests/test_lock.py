"""tests of pyodide-lock customization"""

from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any
import pytest
from copy import deepcopy

from .conftest import WHEELS

if TYPE_CHECKING:
    from pytest_console_scripts import ScriptRunner, RunResult
    from pathlib import Path
    from collections.abc import Callable

    TLockRunner = Callable[[list[str], int], RunResult]
    TPostRun = Callable[[Path, TLockRunner], None]

#: a valid timestamp for IPython 9.11.0
IPY911_EPOCH = 1_772_814_229
#: a set of de-normalized specs for IPython 9.11.0 to override the pyodide defaults
IPY911 = [
    "IPython ==9.11.0",
    "jedi >=0.18.2",
    "matplotlib_inline >=0.1.6",
    "Pygments >=2.14.0",
]
IPY_WHEELS = {
    "ipython_pygments_lexer",
    "ipython",
    "pygments",
    "jedi",
}
PLA = "PyodideLockAddon"
LBC = "LiteBuildConfig"
PLO = "pyodide_lock_options"
TSE = "the_smallest_extension"
IPY = "ipython"

CONFIGS: dict[str, dict[str, dict[str, Any]]] = dict(
    defaults={},
    wheel={PLA: {"wheels": [f"{WHEELS[0]}"]}},
    wheels={PLA: {"wheels": [f"{WHEELS[0].parent}"]}},
    ipy911_specs={PLA: {"specs": IPY911}, LBC: {"source_date_epoch": IPY911_EPOCH}},
    ipy911_constraints={PLA: {PLO: {"constraints": IPY911}}},
)

CONFIG_EXPECT_WHEEL_STEMS: dict[str, set[str]] = dict(
    defaults=set(),
    wheel={TSE},
    wheels={TSE},
    ipy911_specs=IPY_WHEELS,
    ipy911_constraints=IPY_WHEELS,
)

CONFIG_POST: dict[str, Callable[[], list[TPostRun]]] = dict(
    ipy911_specs=lambda: [break_ipython_lock],
)


def test_pyodide_lock(
    some_post_run_checks: list[TPostRun],
    an_empty_lite_dir: Path,
    run_with_lock: TLockRunner,
    a_lock_config: str,
) -> None:
    """can we generate a custom pyodide-lock.json?"""
    expect_wheels = CONFIG_EXPECT_WHEEL_STEMS[a_lock_config]

    run_with_lock(["status"], 0)
    run_with_lock(["build"], 0)

    wheels = {
        w.name.split("-")[0]
        for w in (an_empty_lite_dir / "_output/static/pyodide-lock").glob("*.whl")
    }
    assert wheels == expect_wheels

    run_with_lock(["check"], 0)

    for post in some_post_run_checks:
        post(an_empty_lite_dir, run_with_lock)


# fixtures
@pytest.fixture(params=sorted(CONFIGS))
def a_lock_config(request: pytest.FixtureRequest, has_pyodide_lock_uv: bool) -> str:
    """Provide a key from CONFIG."""
    return f"{request.param}"


@pytest.fixture
def some_post_run_checks(a_lock_config: str) -> list[TPostRun]:
    get_custom = CONFIG_POST.get(a_lock_config)
    return [check_paths, *(get_custom() if get_custom else [])]


@pytest.fixture
def run_with_lock(
    a_lock_config: str,
    an_empty_lite_dir: Path,
    a_pyodide_tarball: str,
    script_runner: ScriptRunner,
) -> TLockRunner:
    """Provide a pre-configured runner."""
    conf_path = an_empty_lite_dir / "jupyter_lite_config.json"
    conf = deepcopy(CONFIGS[a_lock_config])
    conf.setdefault(PLA, {}).update(enabled=True)
    conf.setdefault("PyodideAddon", {}).update(pyodide_url=f"{a_pyodide_tarball}")
    conf_path.write_text(json.dumps(conf), encoding="utf-8")

    def run(args: list[str], expect_rc: int = 0) -> RunResult:
        res = script_runner.run(["jupyter", "lite", *args], cwd=an_empty_lite_dir)
        rc = res.returncode
        assert rc == expect_rc, f"did not return {expect_rc} from {args}"
        return res

    return run


# post-run checks
def check_paths(an_empty_lite_dir: Path, run: TLockRunner) -> None:
    """Check whether key paths exist."""
    static = an_empty_lite_dir / "_output/static"
    pyodide_path = static / "pyodide/pyodide.js"
    lock_path = static / "pyodide-lock/pyodide-lock.json"
    assert pyodide_path.exists(), "pyodide.js does not exist"
    assert lock_path.exists(), "pyodide-lock.json does not exist"


def break_ipython_lock(an_empty_lite_dir: Path, run: TLockRunner) -> None:
    """Break a bunch of things."""
    static = an_empty_lite_dir / "_output/static"
    lock_path = static / "pyodide-lock/pyodide-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"][IPY]["sha256"] = "not-a-sha"
    lock["packages"].pop("jedi")
    next(lock_path.parent.glob("matplotlib*.whl")).unlink()
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
    res = run(["doit", "--", "-s", "check"], 1)
    assert f"[{IPY}] SHA256 mismatch" in res.stderr
    assert f"[{IPY}] missing dependency: jedi" in res.stderr
    assert "[matplotlib-inline] missing wheel" in res.stderr
    lock_path.unlink()
    res = run(["doit", "--", "-s", "check"], 1)
    lock.pop("info")
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
    assert "Failed to parse lock with pyodide-lock" in res.stderr
