// @ts-check

module.exports = /** @type { import('webpack').Configuration } */ ({
  devtool: 'source-map',
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
