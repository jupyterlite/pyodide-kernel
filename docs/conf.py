# -*- coding: utf-8 -*-

extensions = [
    'jupyterlite_sphinx'
]

master_doc = 'index'
source_suffix = '.rst'

project = 'jupyterlite-pyodide-kernel'
copyright = 'JupyterLite Team'
author = 'JupyterLite Team'

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