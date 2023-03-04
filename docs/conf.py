# -*- coding: utf-8 -*-
import tomllib
from pathlib import Path
PY_PROJ = tomllib.read((Path(__file__).parent / "pyproject.toml").open("rb"))


extensions = [
    'jupyterlite_sphinx'
]

master_doc = 'index'
source_suffix = '.md'

project = PY_PROJ["project"]["name"]
copyright = authors = PY_PROJ["project"]["authors"][0]["name"]

exclude_patterns = []

html_theme = "pydata_sphinx_theme"

jupyterlite_dir = "."

# TODO: add the pyodide logo
# html_theme_options = {
#    "logo": {
#       "image_light": "TODO",
#       "image_dark": "TODO",
#    }
# }
