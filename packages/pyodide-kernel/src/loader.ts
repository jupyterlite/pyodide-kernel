// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import type Pyodide from 'pyodide';

/**
 * Import the Pyodide ES module from a URL only known at runtime.
 *
 * Pyodide 314.0.0 and later is ESM-only and must be loaded from its
 * `pyodide.mjs` entry point, see
 * https://blog.pyodide.org/posts/314-release/. The `import()` call is
 * wrapped in `new Function` to keep it out of bundler static analysis,
 * which would otherwise rewrite it into a module lookup that cannot
 * resolve a runtime URL. See
 * https://github.com/jupyterlite/pyodide-kernel/pull/294 for details.
 */
export async function importPyodideModule(url: string): Promise<typeof Pyodide> {
  const dynamicImport = new Function('url', 'return import(url)') as (
    url: string,
  ) => Promise<typeof Pyodide>;
  return dynamicImport(url);
}
