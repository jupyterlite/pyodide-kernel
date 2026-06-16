// @ts-check

module.exports = /** @type { import('@rspack/core').Configuration } */ ({
  devtool: 'source-map',
  optimization: {
    // Disable realContentHash to avoid "circular hash dependency" error
    // when bundling worker files that contain hash-like strings
    // TODO: remove if handled upstream? https://github.com/jupyterlab/jupyterlab/issues/18245
    realContentHash: false,
  },
  module: {
    rules: [
      {
        // The kernel ships its web workers as complete, self-contained ES
        // modules, built ahead of time with esbuild (see the build:workers
        // scripts in @jupyterlite/pyodide-kernel). We copy them into the
        // build output as plain files instead of letting the base config
        // parse them as JavaScript again. The kernel loads them at runtime
        // with `new Worker(url, { type: 'module' })`, which Pyodide 314 and
        // later requires. See initWorker in pyodide-kernel/src/kernel.ts.
        test: /\.worker\.js$/,
        type: 'asset/resource',
        generator: {
          filename: '[name].[contenthash][ext]',
        },
      },
      {
        test: /pypi\/.*/,
        type: 'asset/resource',
        generator: {
          filename: 'pypi/[name][ext][query]',
        },
      },
      {
        test: /schema\/.*/,
        type: 'asset/resource',
        generator: {
          filename: 'schema/[name][ext][query]',
        },
      },
    ],
  },
});
