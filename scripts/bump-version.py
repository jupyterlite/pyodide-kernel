# Copyright (c) JupyterLite Contributors
# Distributed under the terms of the Modified BSD License

import argparse
import json
from pathlib import Path
from subprocess import run

from packaging.version import parse as parse_version

ENC = dict(encoding="utf-8")
HATCH_VERSION = "hatch version"
ROOT = Path(__file__).parent.parent
PYODIDE_KERNEL_PACKAGE = ROOT / "packages" / "pyodide-kernel"
PYODIDE_PACKAGE_JSON = PYODIDE_KERNEL_PACKAGE / "package.json"
PYODIDE_KERNEL_PY_PACKAGE = PYODIDE_KERNEL_PACKAGE / "py" / "pyodide-kernel"
PIPLITE_PY_PACKAGE = PYODIDE_KERNEL_PACKAGE / "py" / "piplite"


def get_version():
    cmd = run([HATCH_VERSION], capture_output=True, shell=True, check=True, cwd=ROOT)
    return cmd.stdout.decode("utf-8").strip().split("\n")[-1]


def next_version():
    v = parse_version(get_version())
    if v.is_prerelease:
        return f"{v.major}.{v.minor}.{v.micro}{v.pre[0]}{v.pre[1] + 1}"
    return f"{v.major}.{v.minor}.{v.micro + 1}"


def bump():
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    args = parser.parse_args()
    py_version = next_version() if args.version == "next" else args.version
    js_version = (
        py_version.replace("a", "-alpha.").replace("b", "-beta.").replace("rc", "-rc.")
    )

    # bump the Python version with hatch for each package
    for package in [ROOT, PYODIDE_KERNEL_PY_PACKAGE, PIPLITE_PY_PACKAGE]:
        run(f"{HATCH_VERSION} {py_version}", shell=True, check=True, cwd=package)

    # bump the js version
    pyodide_kernel_json = json.loads(PYODIDE_PACKAGE_JSON.read_text(**ENC))
    pyodide_kernel_json["pyodideKernel"]["packages"]["py/pyodide-kernel"] = py_version
    pyodide_kernel_json["pyodideKernel"]["packages"]["py/piplite"] = py_version
    PYODIDE_PACKAGE_JSON.write_text(json.dumps(pyodide_kernel_json, indent=2), **ENC)

    # bump the JS version with lerna
    run(f"yarn run bump:js:version {js_version}", shell=True, check=True)


if __name__ == "__main__":
    bump()
