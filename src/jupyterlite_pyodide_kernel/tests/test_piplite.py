"""tests of various mechanisms of providing federated_extensions"""
import json
import shutil

import pytest
from jupyterlite_core.constants import (
    ALL_JSON,
    JSON_FMT,
    JUPYTER_CONFIG_DATA,
    JUPYTERLITE_IPYNB,
    JUPYTERLITE_JSON,
    JUPYTERLITE_METADATA,
    LITE_PLUGIN_SETTINGS,
    UTF8,
)
from pytest import mark

from jupyterlite_pyodide_kernel.constants import (
    DISABLE_PYPI_FALLBACK,
    PIPLITE_URLS,
    PYODIDE_KERNEL_PLUGIN_ID,
    PYPI_WHEELS,
    REPODATA_JSON,
)

from .conftest import PYODIDE_KERNEL_EXTENSION, WHEELS


def has_wheel_after_build(an_empty_lite_dir, script_runner, install_on_import=False):
    """run a build, expecting the fixture wheel, ``all.json`` (and maybe
    ``repodata.json``) to be there
    """
    build = script_runner.run("jupyter", "lite", "build", cwd=str(an_empty_lite_dir))
    assert build.success

    check = script_runner.run("jupyter", "lite", "check", cwd=str(an_empty_lite_dir))
    assert check.success

    output = an_empty_lite_dir / "_output"

    lite_json = output / JUPYTERLITE_JSON
    lite_data = json.loads(lite_json.read_text(encoding="utf-8"))
    assert lite_data[JUPYTER_CONFIG_DATA][LITE_PLUGIN_SETTINGS][
        PYODIDE_KERNEL_PLUGIN_ID
    ][PIPLITE_URLS], "bad wheel urls"

    wheel_out = output / PYPI_WHEELS
    assert (wheel_out / WHEELS[0].name).exists()
    wheel_index = output / PYPI_WHEELS / ALL_JSON
    wheel_index_text = wheel_index.read_text(encoding="utf-8")
    assert WHEELS[0].name in wheel_index_text, wheel_index_text

    repodata = output / PYPI_WHEELS / REPODATA_JSON
    if install_on_import:
        assert repodata.exists()
    else:
        assert not repodata.exists()


@mark.parametrize(
    "remote,folder",
    [[True, False], [False, False], [False, True]],
)
@mark.parametrize("install_on_import", [True, False])
def test_piplite_urls(
    an_empty_lite_dir,
    script_runner,
    remote,
    folder,
    a_fixture_server,
    install_on_import,
):
    """can we include a single wheel?"""
    ext = WHEELS[0]

    if remote:
        piplite_urls = [f"{a_fixture_server}/{ext.name}"]
    else:
        shutil.copy2(WHEELS[0], an_empty_lite_dir)
        if folder:
            piplite_urls = ["."]
        else:
            piplite_urls = [WHEELS[0].name]

    config = {
        "LiteBuildConfig": {
            "apps": ["lab"],
            # ignore accidental extensions from the env
            "ignore_sys_prefix": True,
            # re-add with the as-built or -shipped extension
            "federated_extensions": [
                str(PYODIDE_KERNEL_EXTENSION),
            ],
        },
        "PipliteAddon": {
            "piplite_urls": piplite_urls,
        },
        "PyodideAddon": {
            "install_on_import": install_on_import,
        },
    }

    (an_empty_lite_dir / "jupyter_lite_config.json").write_text(json.dumps(config))

    has_wheel_after_build(an_empty_lite_dir, script_runner, install_on_import)


def test_lite_dir_wheel(an_empty_lite_dir, script_runner):
    wheel_dir = an_empty_lite_dir / PYPI_WHEELS
    wheel_dir.mkdir()
    shutil.copy2(WHEELS[0], wheel_dir / WHEELS[0].name)

    has_wheel_after_build(an_empty_lite_dir, script_runner)


def test_piplite_cli_fail_missing(script_runner, tmp_path, index_cmd):
    path = tmp_path / "missing"
    build = script_runner.run(*index_cmd, str(path))
    assert not build.success


def test_piplite_cli_empty(script_runner, tmp_path, index_cmd):
    path = tmp_path / "empty"
    path.mkdir()
    build = script_runner.run(*index_cmd, str(path))
    assert not build.success


@pytest.mark.parametrize("in_cwd", [True, False])
def test_piplite_cli_win(script_runner, tmp_path, index_cmd, in_cwd):
    path = tmp_path / "one"
    path.mkdir()
    shutil.copy2(WHEELS[0], path / WHEELS[0].name)
    kwargs = {"cwd": str(path)} if in_cwd else {}
    pargs = [] if in_cwd else [str(path)]
    build = script_runner.run(*index_cmd, *pargs, **kwargs)
    assert build.success
    assert json.loads((path / ALL_JSON).read_text(encoding="utf-8"))


@pytest.fixture(params=[JUPYTERLITE_IPYNB, JUPYTERLITE_JSON])
def a_lite_config_file(request, an_empty_lite_dir):
    return an_empty_lite_dir / request.param


def test_validate_config(script_runner, a_lite_config_file):
    lite_dir = a_lite_config_file.parent
    output = lite_dir / "_output"

    build = script_runner.run("jupyter", "lite", "build", cwd=str(lite_dir))
    assert build.success
    shutil.copy2(output / a_lite_config_file.name, a_lite_config_file)
    first_config_data = a_lite_config_file.read_text(**UTF8)

    check = script_runner.run("jupyter", "lite", "check", cwd=str(lite_dir))
    assert check.success
    second_config_data = a_lite_config_file.read_text(**UTF8)
    assert first_config_data == second_config_data

    whole_file = config_data = json.loads(first_config_data)
    if a_lite_config_file.name == JUPYTERLITE_IPYNB:
        config_data = whole_file["metadata"][JUPYTERLITE_METADATA]

    config_data[JUPYTER_CONFIG_DATA].setdefault(LITE_PLUGIN_SETTINGS, {}).setdefault(
        PYODIDE_KERNEL_PLUGIN_ID, {}
    )[DISABLE_PYPI_FALLBACK] = ["clearly-not-an-boolean"]

    third_config_data = json.dumps(whole_file, **JSON_FMT)
    a_lite_config_file.write_text(third_config_data, **UTF8)
    rebuild = script_runner.run("jupyter", "lite", "build", cwd=str(lite_dir))
    assert rebuild.success

    recheck = script_runner.run("jupyter", "lite", "check", cwd=str(lite_dir))
    assert not recheck.success, third_config_data

    fourth_config_data = a_lite_config_file.read_text(**UTF8)
    assert third_config_data == fourth_config_data, fourth_config_data
