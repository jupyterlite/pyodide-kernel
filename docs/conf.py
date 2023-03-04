try:
    import tomllib
except ImportError:
    import tomli as tomllib

from jupyterlite_pyodide_kernel import __version__

from pathlib import Path

PY_PROJ = tomllib.load((Path(__file__).parent.parent / "pyproject.toml").open("rb"))
P = PY_PROJ["project"]

# standard sphinx metadata
project = P["name"]
copyright = authors = P["authors"][0]["name"]
release = __version__
version = ".".join(release.rsplit(".", 1))
exclude_patterns = []

# extensions
extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

# myst
autosectionlabel_prefix_document = True
myst_heading_anchors = 3
suppress_warnings = ["autosectionlabel.*"]
master_doc = "index"
source_suffix = ".md"

# theme
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "github_url": P["urls"]["Homepage"],
    "use_edit_page_button": True,
    "icon_links": [
        {
            "name": "PyPI",
            "url": P["urls"]["PyPI"],
            "icon": "fa-solid fa-box",
        },
    ],
    "pygment_light_style": "github-light",
    "pygment_dark_style": "github-dark"
}

github_user, github_repo = P["urls"]["Source"].split("/")[-2:]

html_context = {
    "github_user": github_user,
    "github_repo": github_repo,
    "github_version": "main",
    "doc_path": "docs",
}
# rely on the order of these to patch json, labextensions correctly
html_static_path = [
    # as-built assets for testing "hot" downstreams against a PR without rebuilding
    "../dist",
    # as-built application, extensions, contents, and patched jupyter-lite.json
    "../build/docs-app",
]

# TODO: add the pyodide logo
# html_theme_options = {
#    "logo": {
#       "image_light": "TODO",
#       "image_dark": "TODO",
#    }
# }
