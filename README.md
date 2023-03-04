# jupyterlite-pyodide-kernel

[![Github Actions Status](https://github.com/jupyterlite/pyodide-kernel/workflows/Build/badge.svg)](https://github.com/jupyterlite/pyodide-kernel/actions/workflows/build.yml)

A Python kernel for JupyterLite powered by Pyodide

⚠️ 🚧 This is a **work in progress**. The Pyodide kernel is currently being extracted
from the main JupyterLite repository to this repo. See
https://github.com/jupyterlite/jupyterlite/pull/854 for more information.

## Requirements

- JupyterLite >= 0.1.0b15

## Install

To install the extension, execute:

```bash
pip install jupyterlite-pyodide-kernel
```

Then build your JupyterLite site:

```bash
jupyter lite build
```

## Uninstall

To remove the extension, execute:

```bash
pip uninstall jupyterlite-pyodide-kernel
```

## Contributing

### Development install

Note: You will need NodeJS to build the extension package.

```bash
# Clone the repo to your local environment
# Change directory to the jupyterlite-pyodide-kernel directory
# Install package in development mode
python -m pip install -e .

# Link your development version of the extension with JupyterLab
jupyter labextension develop . --overwrite

# Rebuild extension Typescript source after making changes
yarn build
```

You can watch the source directory and run JupyterLab at the same time in different
terminals to watch for changes in the extension's source and automatically rebuild the
extension.

```bash
# Watch the source directory in one terminal, automatically rebuilding when needed
yarn watch
# Run JupyterLab in another terminal
jupyter lab
```

With the watch command running, every saved change will immediately be built locally and
available in your running JupyterLab. Refresh JupyterLab to load the change in your
browser (you may need to wait several seconds for the extension to be rebuilt).

### Development uninstall

```bash
pip uninstall jupyterlite-pyodide-kernel
```

In development mode, you will also need to remove the symlink created by
`jupyter labextension develop` command. To find its location, you can run
`jupyter labextension list` to figure out where the `labextensions` folder is located.
Then you can remove the symlink named `@jupyterlite/pyodide-kernel` within that folder.

### Packaging the extension

See [RELEASE](https://github.com/jupyterlite/pyodide-kernel/blob/main/RELEASE.md)
