"""Well-known (and otherwise) constants used by ``jupyterlite-pyodide-kernel``"""

### Pyodide-specific values
#: the key for PyPI-compatible API responses pointing to wheels
PIPLITE_URLS = "pipliteUrls"
DISABLE_PYPI_FALLBACK = "disablePyPIFallback"
#: the schema for piplite-compatible wheel index
PIPLITE_INDEX_SCHEMA = "piplite.v0.schema.json"
#: the schema for piplite-compatible wheel index
KERNEL_SETTINGS_SCHEMA = "kernel.v0.schema.json"
#: where we put wheels, for now
PYPI_WHEELS = "pypi"
#: the plugin id for the Pydodide kernel labextension
PYODIDE_KERNEL_PLUGIN_ID = "@jupyterlite/pyodide-kernel-extension:kernel"
#: the npm name of the Pyodide kernel
PYODIDE_KERNEL_NPM_NAME = PYODIDE_KERNEL_PLUGIN_ID.split(":")[0]
#: the package.json key for piplite
PKG_JSON_PIPLITE = "piplite"
#: the package.json/piplite key for wheels
PKG_JSON_WHEELDIR = "wheelDir"

#: where we put wheels, for now
PYODIDE_URL = "pyodideUrl"

#: where we put pyodide, for now
PYODIDE = "pyodide"
PYODIDE_JS = "pyodide.js"
PYODIDE_LOCK_STEM = "pyodide-lock"
PYODIDE_LOCK = f"{PYODIDE_LOCK_STEM}.json"
PYODIDE_URL_ENV_VAR = "JUPYTERLITE_PYODIDE_URL"

#: probably only compatible with this version of pyodide
PYODIDE_VERSION = "0.29.3"

#: probably only compatible with this version of python in browser
PYODIDE_PYTHON_VERSION = "3.13"

#: the only kind of noarch wheel piplite understands
NOARCH_WHL = "py3-none-any.whl"

#: the only kind of binary wheel piplite previously understood
EMSCRIPTEN_ABI_WHL = "emscripten_*_wasm32.whl"

#: legacy variable alias
WASM_WHL = EMSCRIPTEN_ABI_WHL

#: the Pyodide ABI wheel is the same as the Emscripten
#: ABI wheel, but with a different platform tag, i.e.,
#  YYYY_buildnumber.
PYODIDE_ABI_WHL = "pyodide_*_wasm32.whl"

ALL_WHL = [NOARCH_WHL, WASM_WHL, PYODIDE_ABI_WHL]

RE_WHEEL_DIST_NAME = r"(?P<name>[a-zA_Z][a-z\d_\-\.]*[^\-])-[\d\.]+.*\.whl"

#: the default fallback URL prefix for pyodide packages
PYODIDE_CDN_URL = f"https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full"

#: the path to ``pyodide-lock``-downloaded wheels
PYODIDE_UV_WHEELS = "_uv_wheels"

#: configuration key for the loadPyodide options
LOAD_PYODIDE_OPTIONS = "loadPyodideOptions"

#: configuration key for the lockfile URL
OPTION_LOCK_FILE_URL = "lockFileURL"

#: configuration key for preloaded packages
OPTION_PACKAGES = "packages"
