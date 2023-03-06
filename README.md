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

## 🚧 This is a **work in progress** 🚧

The Pyodide kernel is currently being extracted from the main JupyterLite repository to
this repo. See the [JupyterLite issue][lite-issue] for background, and the in-progress
[pull request][lite-pr] for current status.

⚠️ below denotes instructions that are **incomplete** or **subject to change**.

[lite-issue]: https://github.com/jupyterlite/jupyterlite/issues/386
[lite-pr]: https://github.com/jupyterlite/jupyterlite/pull/854

## Requirements

- `python >=3.8`
- `jupyterlite >=0.1.0b19`

⚠️ At present, `jupyterlite-pyodide-kernel` is only compatible with the in-development
version mentioned above, and requires `nodejs`

A normal install does _not_ require `nodejs`, but a
[development install](#development-install) does.

## Install

⚠️ `jupyterlite-pyodide-kernel` is **not yet published** on PyPI.

For now, the [contributing guide][contrib] describes how to build the package locally.

~~To install the Pyodide kernel labextension and the CLI addons for `jupyter lite`,
run:~~

```bash
pip install jupyterlite-pyodide-kernel
```

Then build your JupyterLite site:

```bash
jupyter lite build
```

⚠️ The documentation for advanced configuration is available from the main JupyterLite
documentation site:

- [configuring]
- [command line interface][cli]

[configuring]:
  https://jupyterlite.readthedocs.io/en/latest/howto/index.html#configuring-the-python-environment
[cli]: https://jupyterlite.readthedocs.io/en/latest/reference/cli.html

## Uninstall

To remove the extension, run:

```bash
pip uninstall jupyterlite-pyodide-kernel
```

## Development Install

Below is an short overview of getting up and running quickly. Please see the
[contributing guide][contrib] for full details.

### Development Requirements

**Recommended** a Python virtual environment provided by a tool of choice, e.g.

- `virtualenv`
- `mamba`
- `conda`

Ensure the local development environment has:

- `git`
- `nodejs 18`
- `python >=3.8`

### Development Quick Start

```bash
git clone https://github.com/jupyterlite/pyodide-kernel
cd pyodide-kernel
npm run quickstart
```

Then, serve the built demo site, documentation, and test reports with Python's built-in
http server:

```bash
jlpm serve
```

[contrib]: https://github.com/jupyterlite/pyodide-kernel/blob/main/CONTRIBUTING.md
