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

## Requirements

- `python >=3.8`

### Compatibility

#### With Jupyter

| status | `jupyterlite-pyodide-kernel` | `jupyterlite-core` |  `jupyterlab`  |   `notebook`   |  `retrolab`  |
| :----: | :--------------------------: | :----------------: | :------------: | :------------: | :----------: |
|  pre   |           `0.4.*`            |    `>=0.4,<0.5`    | `>=4.2.0,<4.3` | `>=7.2.0,<7.3` |      -       |
| stable |           `0.3.*`            |    `>=0.3,<0.4`    | `>=4.1.1,<4.2` | `>=7.1.0,<7.2` |      -       |
| stable |           `0.2.*`            |    `>=0.2,<0.3`    | `>=4.0.7,<4.1` |  `>=7.0.5,<8`  |      -       |
| stable |           `0.1.*`            |    `>=0.1,<0.2`    |  `>=3.5,<3.6`  |       -        | `>=0.3,<0.4` |

Installing the matching version of JupyterLab with your package manager can help ensure
matching labextension assets and kernel dependencies, even though this kernel does not
yet work in a full, `jupyter_server`-hosted client such as JupyterLab or Notebook.

#### With Pyodide

| `jupyterlite-pyodide-kernel` | `pyodide` | `python` | `emscripten` |
| :--------------------------: | :-------: | :------: | :----------: |
|      `>=0.1.0,<=0.1.1`       | `0.23.*`  | `3.10.*` |   `3.1.29`   |
|      `>=0.1.2,<=0.2.1`       | `0.24.*`  | `3.10.*` |   `3.1.45`   |
|      `>=0.2.2,<=0.2.3`       | `0.25.*`  | `3.11.*` |   `3.1.46`   |
|      `>=0.3.*,<=0.4.0`       | `0.25.*`  | `3.11.*` |   `3.1.46`   |
|      `>=0.4.*,<=0.5.0`       | `0.26.*`  | `3.12.*` |   `3.1.58`   |

Note that the Emscripten version is strict down to the bugfix version.

## Install

To install the Pyodide kernel labextension and the CLI addons for `jupyter lite`, run:

```bash
pip install jupyterlite-pyodide-kernel
```

or with `conda`, `mamba`, `micromamba`, etc.

```bash
conda install -c conda-forge jupyterlite-pyodide-kernel
```

> For more options see the [development install](#development-install) or [contributing
> guide][contrib].

## Usage

Build a JupyterLite site:

```bash
jupyter lite build
```

Some new CLI options are also available:

```bash
jupyter lite --help
```

This should show something like this:

```bash
  --piplite-wheels=<typedtuple-item-1>...
      Local paths or URLs of piplite-compatible wheels to copy and index
      Default: ()
      Equivalent to: [--PipliteAddon.piplite_urls]
  --pyodide=<Unicode>
      Local path or URL of a pyodide distribution tarball
      Default: ''
      Equivalent to: [--PyodideAddon.pyodide_url]
```

## Learn more

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
pip uninstall jupyterlite-pyodide-kernel  # or however you installed it
```

## Prerelease Versions

To install pre-release versions with `pip`:

```bash
pip install --upgrade --pre jupyterlite-pyodide-kernel
```

Or, similarly for the `conda` ecosystem, for `alpha` packages:

```bash
conda install \
  -c conda-forge/label/jupyterlite_core_alpha \
  -c conda-forge/label/jupyterlite_pyodide_kernel_alpha \
  -c conda-forge \
  jupyterlite-pyodide-kernel
```

> Note: `_beta` and `_rc` packages would follow a similar channel naming convention

## Development Install

Below is an short overview of getting up and running quickly. Please see the
[contributing guide][contrib] for full details.

### Development Requirements

**Recommended** a Python virtual environment provided by a tool of choice, e.g. one of:

- `virtualenv`
- `mamba`
- `conda`

Ensure the local development environment has:

- `git`
- `nodejs 20`
- `python >=3.8`

### Development Quick Start

```bash
git clone https://github.com/jupyterlite/pyodide-kernel
cd pyodide-kernel
npm run quickstart
```

Then, serve the built demo site, documentation, and test reports with Python's built-in
HTTP server:

```bash
jlpm serve
```

[contrib]: https://github.com/jupyterlite/pyodide-kernel/blob/main/CONTRIBUTING.md
