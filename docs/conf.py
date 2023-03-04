try:
    import tomllib
except ImportError:
    import tomli as tomllib

from jupyterlite_pyodide_kernel import __version__

from pathlib import Path

PY_PROJ = tomllib.load((Path(__file__).parent.parent / "pyproject.toml").open("rb"))
P = PY_PROJ["project"]

project = P["name"]
copyright = authors = P["authors"][0]["name"]

release = __version__

# The short X.Y version
version = ".".join(release.rsplit(".", 1))


extensions = [
    "jupyterlite_sphinx",
    "myst_parser",
]

master_doc = "index"
source_suffix = ".md"

exclude_patterns = []

# theme
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "github_url": P["urls"]["Homepage"],
    "use_edit_page_button": True,
}

github_user, github_repo = P["urls"]["Source"].split("//")[1].split("/")

html_context = {
    "github_user": github_user,
    "github_repo": github_repo,
    "github_version": "main",
    "doc_path": "docs",
}

# lite
jupyterlite_dir = "."

# myst
autosectionlabel_prefix_document = True
myst_heading_anchors = 3
suppress_warnings = ["autosectionlabel.*"]


# TODO: add the pyodide logo
# html_theme_options = {
#    "logo": {
#       "image_light": "TODO",
#       "image_dark": "TODO",
#    }
# }
