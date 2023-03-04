# Copyright (c) JupyterLite Contributors
# Distributed under the terms of the Modified BSD License

import argparse
import json

from pathlib import Path
from subprocess import run

ENC = dict(encoding="utf-8")
ROOT = Path(__file__).parent.parent
PYODIDE_KERNEL_PACKAGE = ROOT / "packages" / "pyodide-kernel"
PYODIDE_PACKAGE_JSON = PYODIDE_KERNEL_PACKAGE / "package.json"
PYODIDE_KERNEL_PY_PACKAGE = PYODIDE_KERNEL_PACKAGE / "py" / "pyodide-kernel"
PIPLITE_PY_PACKAGE = PYODIDE_KERNEL_PACKAGE / "py" / "piplite"


def bump():
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    args = parser.parse_args()
    py_version = args.version
    js_version = (
        py_version.replace("a", "-alpha.").replace("b", "-beta.").replace("rc", "-rc.")
    )

    # bump the Python version with hatch for each package
    for package in [ROOT, PYODIDE_KERNEL_PY_PACKAGE, PIPLITE_PY_PACKAGE]:
        run(f"hatch version {py_version}", shell=True, check=True, cwd=package)

    # bump the js version
    pyolite_json = json.loads(PYODIDE_PACKAGE_JSON.read_text(**ENC))
    pyolite_json["pyodide-kernel"]["packages"]["py/pyodide-kernel"] = py_version
    pyolite_json["pyodide-kernel"]["packages"]["py/piplite"] = py_version
    PYODIDE_PACKAGE_JSON.write_text(json.dumps(pyolite_json, indent=2), **ENC)

    # bump the JS version with lerna
    run(f"yarn run bump:js:version {js_version}", shell=True, check=True)


if __name__ == "__main__":
    bump()
