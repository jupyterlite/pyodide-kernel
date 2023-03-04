# -*- coding: utf-8 -*-

extensions = [
    'jupyterlite_sphinx',
    'myst_parser'
]

master_doc = 'index'
source_suffix = '.md'

project = 'jupyterlite-pyodide-kernel'
copyright = 'JupyterLite Contributors'
author = 'JupyterLite Contributors'

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
