# Contributing

## Prerequisites

- `git`
- `python >=3.8`
- `nodejs >=18,<19`

## Quick Start

The command below cleans out all built artifacts, ensures a fully-configured JS/Python
environment, and generates everything up to the documentation website and test reports.

```bash
git clone https://github.com/jupyterlite/pyodide-kernel
cd pyodide kernel
npm run quickstart
```

> The above installs JupyterLab, which provides the `jlpm` command, a pre-packaged
> version of `yarn`, and is used instead of `npm` from here on out.

### Serve

```bash
jlpm serve
```

> Serve the `build/` directory as `http://127.0.0.1:8000`, which contains:
>
> - `docs-app/` just the built JupyterLite
> - `docs/` the full documentation website
> - `reports/` built reports from tests and static analysis

## Individual steps

### Update/Install Dependencies

#### JS

```bash
jlpm
```

> Run this after changing the `dependencies` or `devDependencies` of any `package.json`
>
> This will update the `yarn.lock` with a reproducible solution to the NodeJS build
> tools and static assets that will be served on the website.

#### Python

```bash
python -m pip install -e .[dev,test,docs]
```

> Run this after changing `pyproject.toml`.

### Build

```bash
jlpm build
```

> Build and install development versions of the JS packages.

### Distributions

```bash
jlpm dist
```

> Build distributions for `pypi.org` and `npmjs.org`.

### Test

Run JS and Python tests.

> TBD
>
> > ```bash
> > jlpm test
> > ```

## Documenation

```bash
jlpm docs
```

> Build the JupyterLite site and a Sphinx site which includes the JupyterLite site.

## Clean

```bash
jlpm clean:all
```

> Removes all built assets.
