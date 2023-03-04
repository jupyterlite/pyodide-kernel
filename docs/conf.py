# -*- coding: utf-8 -*-

extensions = [
    'jupyterlite_sphinx'
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

def on_config_inited(*args):
    import sys
    import subprocess
    from pathlib import Path

    HERE = Path(__file__)
    ROOT = HERE.parent.parent
    subprocess.check_call([sys.executable, "-m", "pip", "install", "\".[dev]\""], cwd=str(ROOT))
    subprocess.check_call(["yarn"], cwd=str(ROOT))
    subprocess.check_call(["yarn", "build"], cwd=str(ROOT))


def setup(app):
    app.connect("config-inited", on_config_inited)
