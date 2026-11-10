"""A configurable Python package backed by Pyodide's micropip"""

from .piplite import install

__version__ = "0.9.0b0"

__all__ = ["__version__", "install"]
