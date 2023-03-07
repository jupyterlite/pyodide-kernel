"""Well-known (and otherwise) constants used by JupyterLite"""

### pyolite-specific values, will move to separate repo
#: the key for PyPI-compatible API responses pointing to wheels
PIPLITE_URLS = "pipliteUrls"
#: the schema for piplite-compatible wheel index
PIPLITE_INDEX_SCHEMA = "piplite.schema.v0.json"
#: where we put wheels, for now
PYPI_WHEELS = "pypi"
#: the plugin id for the pyolite kernel
PYOLITE_PLUGIN_ID = "@jupyterlite/pyolite-kernel-extension:kernel"
#: the package.json key for piplite
PKG_JSON_PIPLITE = "piplite"
#: the package.json/piplite key for wheels
PKG_JSON_WHEELDIR = "wheelDir"

#: where we put wheels, for now
PYODIDE_URL = "pyodideUrl"

#: where we put pyodide, for now
PYODIDE = "pyodide"
PYODIDE_JS = "pyodide.js"
PYODIDE_REPODATA = "repodata.json"
PYODIDE_URL_ENV_VAR = "JUPYTERLITE_PYODIDE_URL"

#: probably only compatible with this version of pyodide
PYODIDE_VERSION = "0.23.0a1"

#: the only kind of noarch wheel piplite understands
NOARCH_WHL = "py3-none-any.whl"

#: the only kind of binary wheel piplite understands
WASM_WHL = "emscripten_*_wasm32.whl"

ALL_WHL = [NOARCH_WHL, WASM_WHL]
