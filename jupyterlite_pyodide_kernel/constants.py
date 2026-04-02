"""Well-known (and otherwise) constants used by ``jupyterlite-pyodide-kernel``"""

### Pyodide-specific values
#: the key for PyPI-compatible API responses pointing to wheels
PIPLITE_URLS = "pipliteUrls"
DISABLE_PYPI_FALLBACK = "disablePyPIFallback"
#: the schema for piplite-compatible wheel index
PIPLITE_INDEX_SCHEMA = "piplite.v0.schema.json"
#: the schema for the Pyodide kernel settings
KERNEL_SETTINGS_SCHEMA = "kernel.v0.schema.json"
#: where we put wheels, for now
PYPI_WHEELS = "pypi"
#: the plugin id for the Pyodide kernel labextension
PYODIDE_KERNEL_PLUGIN_ID = "@jupyterlite/pyodide-kernel-extension:kernel"
#: the npm name of the Pyodide kernel
PYODIDE_KERNEL_NPM_NAME = PYODIDE_KERNEL_PLUGIN_ID.split(":")[0]
#: the package.json key for piplite
PKG_JSON_PIPLITE = "piplite"
#: the package.json/piplite key for wheels
PKG_JSON_WHEELDIR = "wheelDir"

#: the jupyter-lite.json config key for the Pyodide base URL
PYODIDE_URL = "pyodideUrl"

#: directory name and filenames for the Pyodide distribution
PYODIDE = "pyodide"
PYODIDE_JS = "pyodide.js"
PYODIDE_LOCK = "pyodide-lock.json"
PYODIDE_URL_ENV_VAR = "JUPYTERLITE_PYODIDE_URL"

#: probably only compatible with this version of pyodide
PYODIDE_VERSION = "0.29.3"

#: the only kind of noarch wheel piplite understands
NOARCH_WHL = "py3-none-any.whl"

#: [pyodide <0.26] the raw Emscripten platform tag (emscripten_*_wasm32),
#: predating both the pyodide_ and pyemscripten_ platform tags
EMSCRIPTEN_ABI_WHL = "emscripten_*_wasm32.whl"

#: variable alias for EMSCRIPTEN_ABI_WHL
WASM_WHL = EMSCRIPTEN_ABI_WHL

#: [pyodide <0.30] [micropip <0.11.1] the Pyodide-specific platform tag
#: (pyodide_*_wasm32); kept for backward compatibility, superseded by
#: PYEMSCRIPTEN_ABI_WHL following PEP 783:
#: https://peps.python.org/pep-0783/
#: https://github.com/pyodide/micropip/pull/270
PYODIDE_ABI_WHL = "pyodide_*_wasm32.whl"

#: [pyodide >=0.30] [micropip >=0.11.1] the PEP 783 platform tag
#: (pyemscripten_*_wasm32); pyodide-build produces these by default
#: and micropip accepts them via updated sys_tags():
#: https://peps.python.org/pep-0783/
#: https://github.com/pyodide/micropip/pull/270
#: https://github.com/pyodide/pyodide-build/pull/319
PYEMSCRIPTEN_ABI_WHL = "pyemscripten_*_wasm32.whl"

ALL_WHL = [NOARCH_WHL, WASM_WHL, PYODIDE_ABI_WHL, PYEMSCRIPTEN_ABI_WHL]
