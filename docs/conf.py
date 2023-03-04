try:
    import tomllib
except ImportError:
    import tomli as tomllib

from pathlib import Path

PY_PROJ = tomllib.load((Path(__file__).parent.parent / "pyproject.toml").open("rb"))
P = PY_PROJ["project"]

extensions = [
    "jupyterlite_sphinx",
    "myst_parser",
]

master_doc = "index"
source_suffix = ".md"

project = P["name"]
copyright = authors = P["authors"][0]["name"]

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
