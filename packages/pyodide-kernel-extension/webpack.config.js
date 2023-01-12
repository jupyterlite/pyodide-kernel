module.exports = {
  module: {
    rules: [
      {
        test: /\.whl$/,
        type: 'asset/resource',
        generator: {
          filename: 'pypi/[name].[ext]',
        },
      },
    ],
  },
};
