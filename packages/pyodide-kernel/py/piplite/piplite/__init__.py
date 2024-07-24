"""A configurable Python package backed by Pyodide's micropip"""

from .piplite import install

__version__ = "0.4.0rc0"

__all__ = ["install", "__version__"]
