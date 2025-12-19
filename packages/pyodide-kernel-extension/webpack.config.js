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
