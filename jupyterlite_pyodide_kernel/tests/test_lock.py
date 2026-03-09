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
    TPostRun = Callable[[Path, str, TLockRunner], None]

# paths
PL = "pyodide-lock"
PLJ = "pyodide-lock.json"
SPLJ = f"_output/static/{PL}/{PLJ}"
SPJS = "_output/static/pyodide/pyodide.js"
JLCJ = "jupyter_lite_config.json"

#: a valid timestamp for IPython 9.11.0
IPY911_EPOCH = 1_772_814_229
#: a set of de-normalized specs for IPython 9.11.0 to override the pyodide defaults
IPY911_SPECS = [
    "IPython ==9.11.0",
    "jedi >=0.18.2",
    "matplotlib_inline >=0.1.6",
    "Pygments >=2.14.0",
]
PA = "PyodideAddon"
LBC = "LiteBuildConfig"
LCO = "lock_compile_options"
TSE = "the_smallest_extension"
IPY = "ipython"
IPW = "ipywidgets"

CONFIGS: dict[str, dict[str, dict[str, Any]]] = dict(
    #: enabled, no other configuration
    defaults={},
    #: a single local wheel with no dependencies
    wheel={PA: {"lock_wheels": [f"{WHEELS[0]}"]}},
    #: a single folder containing a wheel
    wheels={PA: {"lock_wheels": [f"{WHEELS[0].parent}"]}},
    #: specs for a specific version of IPython, not inlcuded in any Pyodide distribution
    ipy911_specs={
        PA: {"lock_specs": IPY911_SPECS},
        LBC: {"source_date_epoch": IPY911_EPOCH},
    },
    #: constraints for a specific version of IPython, not inlcuded in any Pyodide distribution
    ipy911_constraints={PA: {"lock_constraints": IPY911_SPECS}},
    #: ipywidgets
    widgets={PA: {"lock_specs": [IPW]}},
    #: wherever possible, use any publicly-available URL instead of locally-cached copies
    all_remote={PA: {LCO: {"preserve_url_prefixes": ["https://"]}}},
)

#: keys of CONFIGS that should not use the test fixture tarball
CONFIG_NO_TARBALL: set[str] = {"all_remote"}

#: the PyPI dependencies of ``pyodide_kernel`` not included in the current Pyodide distribution
DEFAULT_WHEELS = {"comm", "ipython_pygments_lexers"}
#: additional wheels expected for a specific version of IPython
IPY911_WHEELS = {"ipython", "pygments", "jedi", "matplotlib_inline"}

#: wheels to expect in the ``static/pyodide-lock`` folder after a build
CONFIG_EXPECT_WHEEL_STEMS: dict[str, set[str]] = dict(
    defaults=DEFAULT_WHEELS,
    wheel={TSE, *DEFAULT_WHEELS},
    wheels={TSE, *DEFAULT_WHEELS},
    ipy911_specs={*IPY911_WHEELS, *DEFAULT_WHEELS},
    ipy911_constraints={*IPY911_WHEELS, *DEFAULT_WHEELS},
    widgets={IPW, *DEFAULT_WHEELS},
    all_remote=set(),
)

#: extra checks to perform
CONFIG_POST: dict[str, Callable[[], list[TPostRun]]] = dict(
    ipy911_specs=lambda: [break_ipython_lock],
)


def test_pyodide_lock(
    some_post_run_checks: list[TPostRun],
    an_empty_lite_dir: Path,
    run_with_lock: TLockRunner,
    a_lock_config: str,
) -> None:
    """can we generate a custom Pyodide lockfile?"""
    run_with_lock(["status"], 0)
    run_with_lock(["build"], 0)
    run_with_lock(["check"], 0)

    for post in some_post_run_checks:
        post(an_empty_lite_dir, a_lock_config, run_with_lock)


# fixtures
@pytest.fixture(params=sorted(CONFIGS))
def a_lock_config(request: pytest.FixtureRequest, has_pyodide_lock_uv: bool) -> str:
    """Provide a key from ``CONFIGS`` above."""
    return f"{request.param}"


@pytest.fixture
def some_post_run_checks(a_lock_config: str) -> list[TPostRun]:
    get_custom = CONFIG_POST.get(a_lock_config)
    return [check_paths, check_lock, *(get_custom() if get_custom else [])]


@pytest.fixture
def run_with_lock(
    a_lock_config: str,
    an_empty_lite_dir: Path,
    a_pyodide_tarball: str,
    script_runner: ScriptRunner,
) -> TLockRunner:
    """Provide a pre-configured script runner."""
    conf = deepcopy(CONFIGS[a_lock_config])
    pyodide_config = conf.setdefault(PA, {})
    pyodide_url = None if a_lock_config in CONFIG_NO_TARBALL else f"{a_pyodide_tarball}"
    pyodide_config.update(lock_enabled=True, pyodide_url=pyodide_url)
    pyodide_config.setdefault(LCO, {}).update(debug=True)
    (an_empty_lite_dir / JLCJ).write_text(json.dumps(conf), encoding="utf-8")

    def run(args: list[str], expect_rc: int = 0) -> RunResult:
        res = script_runner.run(["jupyter", "lite", *args], cwd=an_empty_lite_dir)
        rc = res.returncode
        ok = rc == expect_rc
        if not ok:
            cache_dir = an_empty_lite_dir / ".cache/pyodide-lock"
            paths = map(str, sorted(cache_dir.rglob("*.*")))
            print("\n".join(["cached paths", *paths]))
        assert ok, f"did not return {expect_rc} from {args}"
        return res

    return run


# post-run checks
def check_paths(an_empty_lite_dir: Path, a_lock_config: str, run: TLockRunner) -> None:
    """Check whether key paths exist."""
    pyodide_path = an_empty_lite_dir / SPJS
    if a_lock_config in CONFIG_NO_TARBALL:
        assert not pyodide_path.exists(), f"{SPJS} should NOT exist"
    else:
        assert pyodide_path.exists(), f"{SPJS} should exist"

    lock_path = an_empty_lite_dir / SPLJ
    assert lock_path.exists(), f"{SPLJ} should exist"

    expect_wheels = CONFIG_EXPECT_WHEEL_STEMS[a_lock_config]
    wheels = sorted(lock_path.parent.glob("*.whl"))
    wheel_names = {w.name.split("-")[0] for w in wheels}
    extra_wheels = wheel_names - expect_wheels
    missing_wheels = expect_wheels - wheel_names
    assert not missing_wheels, "not enough wheels after build"
    assert not extra_wheels, "too many wheels after build"


def check_lock(an_empty_lite_dir: Path, a_lock_config: str, run: TLockRunner) -> None:
    """Check some properties of the lock."""
    lock = json.loads((an_empty_lite_dir / SPLJ).read_text(encoding="utf-8"))
    assert "widgetsnbextension" not in lock["packages"]
    assert "jupyterlab-widgets" not in lock["packages"]


def break_ipython_lock(
    an_empty_lite_dir: Path, a_lock_config: str, run: TLockRunner
) -> None:
    """Break a bunch of things."""
    lock_path = an_empty_lite_dir / SPLJ
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["packages"].pop("jedi")
    next(lock_path.parent.glob("matplotlib*.whl")).unlink()
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
    res = run(["doit", "--", "-s", "check"], 1)
    assert f"[{IPY}] missing dependency: jedi" in res.stderr
    assert "[matplotlib-inline] missing wheel" in res.stderr
    lock_path.unlink()
    res = run(["doit", "--", "-s", "check"], 1)
    lock.pop("info")
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True), encoding="utf-8")
    res = run(["doit", "--", "-s", "check"], 1)
    assert "Failed to parse lock with pyodide-lock" in res.stderr
