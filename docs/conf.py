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
html_logo =  "../packages/pyodide-kernel-extension/style/img/pyodide.svg"
html_favicon = html_logo
html_theme_options = {
    "github_url": P["urls"]["Source"],
    "icon_links": [
       {"name": "PyPI", "url": P["urls"]["PyPI"], "icon": "fa-solid fa-box"}
    ],
    "logo": {
        "text": P["name"]
    },
    "navigation_with_keys": False,
    "pygment_light_style": "github-light",
    "pygment_dark_style": "github-dark",
    "use_edit_page_button": True,
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
    "./_static",
    # as-built assets for testing "hot" downstreams against a PR without rebuilding
    "../dist",
    # as-built application, extensions, contents, and patched jupyter-lite.json
    "../build/docs-app",
]

html_css_files = [
    "variables.css",
]
