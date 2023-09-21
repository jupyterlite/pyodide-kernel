"""A configurable Python package backed by Pyodide's micropip"""
from .piplite import install

__version__ = "0.2.0a1"

__all__ = ["install", "__version__"]
