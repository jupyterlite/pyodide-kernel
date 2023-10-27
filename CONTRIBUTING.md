# Contributing

The final, user-facing products of `jupyterlite-pyodide-kernel` are:

- the [distribution](#distributions) on `pypi.org` and `npmjs.org`
- the [documentation](#documentation) on ReadTheDocs

Preparing for a [release], however, requires a number of intermediate steps.

**Recommended**: Start with the (almost) single-line [quick start](#quick-start) script,
and watch what it does to files on disk and in the terminal log.

[release]: https://github.com/jupyterlite/pyodide-kernel/blob/main/RELEASE.md

## Quick Start

### Prerequisites

- `git`
- `python >=3.8`
- `nodejs >=20,<21`

### Setup

```bash
git clone https://github.com/jupyterlite/pyodide-kernel
cd pyodide-kernel
npm run quickstart
```

### Serve

```bash
jlpm serve
```

| provides                 | requires                                                       |
| ------------------------ | -------------------------------------------------------------- |
| a development web server | [install](#dependencies)<br/>[build](#build)<br/>[demo](#demo) |

Serve the `build/` directory as `http://127.0.0.1:8000`, which contains:

- `docs-app/` just the built JupyterLite
- `docs/` the full documentation website
- `reports/` built reports from tests and static analysis

## Individual Steps

`npm run quickstart` will, in the correct order:

- [clean](#clean) out any pre-existing built artifacts and caches
- ensure local Python and NodeJS has all required [dependencies](#dependencies) for
  development
- [build](#build) the underlying JS/CSS assets that will be served to the browser in a
  JupyterLite site
- build [distributions](#distributions) ready for on `pypi.org` and `npmjs.org`
- a minimal JupyterLite [demo](#demo) site with
  - `pyodide-core`, a lightweight Pyodide distribution (5mb vs 250mb)
  - the `@jupyter-widget/jupyterlab-manager` extension enabled
- the [documentation](#documentation) website (including the demo)
- [test](#test) the code and generate HTML reports

### Dependencies

#### Python

```bash
python -m pip install -e .[dev,test,docs]
```

| provides | requires                        | run after changing |
| -------- | ------------------------------- | ------------------ |
| `jlpm`   | [prerequisites](#prerequisites) | `pyproject.toml`   |

The above installs JupyterLab, which provides the `jlpm` command, a pre-packaged version
of `yarn`, and is used instead of `npm` from here on out.

#### JavaScript

```bash
jlpm
```

| provides       | requires                      | run after changing |
| -------------- | ----------------------------- | ------------------ |
| `node_modules` | [install](#dependencies)<br/> | `package.json`     |

Run this after changing the `dependencies` or `devDependencies` of any `package.json`

This will update the `yarn.lock` with a reproducible solution to the NodeJS build tools
and static assets that will be served on the website.

Run this after changing `pyproject.toml`.

### Build

```bash
jlpm build
# or
jlpm build:prod
```

| provides                                                           | requires                      | run after changing                                       |
| ------------------------------------------------------------------ | ----------------------------- | -------------------------------------------------------- |
| `packages/*/lib/*.js`<br/>`jupyterlab_pyodide_kernel/labextension` | [install](#dependencies)<br/> | `packages/*/src/**/*.tsx?`<br/>`packages/*/style/**/*.*` |

Build and install development versions of the JS packages and lab extension.

### Distributions

```bash
jlpm dist
```

| provides | requires        | run after changing                              |
| -------- | --------------- | ----------------------------------------------- |
| `dist`   | [build](#build) | `packages/*`<br/>`jupyterlite_pyodide_kernel/*` |

Build distributions for `pypi.org` and `npmjs.org`.

### Test

```bash
jlpm test
```

| provides | requires        | run after changing             |
| -------- | --------------- | ------------------------------ |
| `dist`   | [build](#build) | `jupyterlite_pyodide_kernel/*` |

Run JS and Python tests.

## Sites

```bash
jlpm docs
```

Builds both sites described below.

### Demo

```bash
jlpm docs:lite
```

| provides         | requires        | run after changing                                               |
| ---------------- | --------------- | ---------------------------------------------------------------- |
| `build/docs-app` | [build](#build) | `packages/*`<br/>`jupyterlite_pyodide_kernel/*`<br/>`examples/*` |

Build a minimal JupyterLite demo site.

As a JupyterLite "server" extension, `@jupyterlite/pyodide-kernel` will have _no effect_
on a "vanilla" JupyterLab installation, so this is the closest experience to
`jupyter labextension develop` currently available.

### Documentation

```bash
jlpm docs:sphinx
```

| provides     | requires      | run after changing                                                          |
| ------------ | ------------- | --------------------------------------------------------------------------- |
| `build/docs` | [demo](#demo) | `packages/*`<br/>`jupyterlite_pyodide_kernel/*`<br/>`examples/*`<br/>`docs` |

Build a site in `build/docs` with Sphinx which includes a copy of the JupyterLite site.

## Clean

```bash
jlpm clean:all
```

| provides | requires                 | run after                       |
| -------- | ------------------------ | ------------------------------- |
| -        | [install](#dependencies) | anything that seems out-of-date |

Removes all built assets, caches, etc. `node_modules` _won't_ be cleaned out

### Cleaner

```bash
jlpm cache clean
rm -rf node_modules
```
