# Contributing

## Prerequisites

- `python >=3.8`
- `nodejs >=18,<19`

## Quick Start

This cleans out all built artifacts, ensures a fully-configured JS/Python environment,
and generates everything up to the documentation website.

```bash
git clone https://github.com/jupyterlite/pyodide-kernel
cd pyodide kernel
npm run quickstart
```

### Serve

```bash
jlpm serve
```

## Individual steps

### Build

Build and install development versions of the JS packages.

```bash
jlpm build
```

### Distributions

Build distributions for `pypi.org` and `npmjs.org`.

```bash
jlpm dist
```

### Test

Run JS and Python tests.

> TBD
>
> > ```bash
> > jlpm test
> > ```

## Documenation

Build the JupyterLite site and a Sphinx site which includes the JupyterLite site.

```bash
jlpm docs
```
