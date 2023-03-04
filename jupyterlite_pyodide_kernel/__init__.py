from ._version import __version__  # noqa


def _jupyter_labextension_paths():
    return [{"src": "labextension", "dest": "@jupyterlite/pyodide-kernel"}]
