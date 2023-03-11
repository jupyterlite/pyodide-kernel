"""Well-known (and otherwise) constants used by ``jupyterlite-pyodide-kernel``"""
from typing import Dict, List

### pyodide-specific values
#: the key for PyPI-compatible API responses pointing to wheels
PIPLITE_URLS = "pipliteUrls"
DISABLE_PYPI_FALLBACK = "disablePyPIFallback"
#: the schema for piplite-compatible wheel index
PIPLITE_INDEX_SCHEMA = "piplite.v0.schema.json"
#: the schema for piplite-compatible wheel index
REPODATA_SCHEMA = "repodata.v0.schema.json"
#: the schema for piplite-compatible wheel index
KERNEL_SETTINGS_SCHEMA = "kernel.v0.schema.json"
#: where we put wheels, for now
PYPI_WHEELS = "pypi"
#: the plugin id for the pydodide kernel labextension
PYODIDE_KERNEL_PLUGIN_ID = "@jupyterlite/pyodide-kernel-extension:kernel"
#: the npm name of the pyodide kernel
PYODIDE_KERNEL_NPM_NAME = PYODIDE_KERNEL_PLUGIN_ID.split(":")[0]
#: the package.json key for pyodide-kernel metadata
PKG_JSON_PYODIDE_KERNEL = "pyodideKernel"
#: the package.json/piplite key for wheels
PKG_JSON_WHEELDIR = "wheelDir"
#: the schema for a pyodide-kernel-compatible ``package.json``
PKG_JSON_SCHEMA = "package.v0.schema.json"

#: where we put wheels, for now
PYODIDE_URL = "pyodideUrl"

#: the key for pyodide-compatible repodata.json
REPODATA_URLS = "repodataUrls"

#: where setuptools wheels store their exported modules
TOP_LEVEL_TXT = "top_level.txt"

#: where all wheels store a list of all exported files
WHL_RECORD = "RECORD"

#: the pyodide index of wheels
REPODATA_JSON = "repodata.json"


#: the observed default environment of pyodide
PYODIDE_MARKER_ENV = {
    "implementation_name": "cpython",
    "implementation_version": "3.10.2",
    "os_name": "posix",
    "platform_machine": "wasm32",
    "platform_release": "3.1.27",
    "platform_system": "Emscripten",
    "platform_version": "#1",
    "python_full_version": "3.10.2",
    "platform_python_implementation": "CPython",
    "python_version": "3.10",
    "sys_platform": "emscripten",
}

TDistPackages = Dict[str, List[str]]


#: where we put pyodide, for now
PYODIDE = "pyodide"
PYODIDE_JS = "pyodide.js"
PYODIDE_REPODATA = "repodata.json"
PYODIDE_URL_ENV_VAR = "JUPYTERLITE_PYODIDE_URL"

#: probably only compatible with this version of pyodide
PYODIDE_VERSION = "0.22.1"

#: the only kind of noarch wheel piplite understands
NOARCH_WHL = "py3-none-any.whl"

#: the only kind of binary wheel piplite understands
WASM_WHL = "emscripten_*_wasm32.whl"

ALL_WHL = [NOARCH_WHL, WASM_WHL]
