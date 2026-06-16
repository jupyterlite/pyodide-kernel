// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * Import an ES module from a URL only known at runtime.
 *
 * The `import()` call is wrapped in `new Function` to keep it out of bundler
 * static analysis, which would otherwise rewrite it into a module lookup that
 * cannot resolve a runtime URL. See
 * https://github.com/jupyterlite/pyodide-kernel/pull/294 for details.
 *
 * This is used to load Pyodide. Pyodide 314.0.0 and later is ESM-only and
 * must be loaded from its `pyodide.mjs` entry point, see
 * https://blog.pyodide.org/posts/314-release/.
 */
export async function importModule<T = unknown>(url: string): Promise<T> {
  const dynamicImport = new Function('url', 'return import(url)') as (
    url: string,
  ) => Promise<T>;
  return dynamicImport(url);
}
