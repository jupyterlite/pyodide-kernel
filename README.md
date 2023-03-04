# jupyterlite-pyodide-kernel

> A Python kernel for [JupyterLite](https://jupyterlite.rtfd.io) powered by
> [Pyodide](https://pyodide.org),

[![ci-badge]][ci] [![lite-badge]][lite] [![docs-badge]][docs]

[ci-badge]: https://github.com/jupyterlite/pyodide-kernel/workflows/Build/badge.svg
[lite-badge]: https://jupyterlite.rtfd.io/en/latest/_static/badge.svg
[lite]: https://jupyterlite-pyodide-kernel.rtfd.io/en/latest/_static
[ci]: https://github.com/jupyterlite/pyodide-kernel/actions?query=branch%3Amain
[docs-badge]:
  https://readthedocs.org/projects/jupyterlite-pyodide-kernel/badge/?version=latest
[docs]: https://jupyterlite-pyodide-kernel.readthedocs.io/en/latest/?badge=latest

> ## ⚠️ 🚧 This is a **work in progress**.
>
> The Pyodide kernel is currently being extracted from the main JupyterLite repository
> to this repo. See https://github.com/jupyterlite/jupyterlite/pull/854 for more
> information.

## Requirements

- python >=3.8

> At present, this is only compatible with
>
> - JupyterLite >=0.1.0b15

## Install

To install the Pyodide kernel labextension and the CLI addons for `jupyter lite`, run:

> This package is not yet published to PyPI. For now, the [contributing guide] describes
> how to build the package locally.
>
> > ```bash
> > pip install jupyterlite-pyodide-kernel
> > ```

Then build your JupyterLite site:

```bash
jupyter lite build
```

> For now, the documentation for advanced configuration is available from the main
> JupyterLite documentation site:
>
> - [configuring]
> - [command line interface][cli]

[configuring]:
  https://jupyterlite.readthedocs.io/en/latest/howto/index.html#configuring-the-python-environment
[cli]: https://jupyterlite.readthedocs.io/en/latest/reference/cli.html

## Uninstall

To remove the extension, run:

```bash
pip uninstall jupyterlite-pyodide-kernel
```

## Contributing

> See the [contributing guide].

[contributing guide]:
  https://github.com/jupyterlite/pyodide-kernel/blob/main/CONTRIBUTING.md
