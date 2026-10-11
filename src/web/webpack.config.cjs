const fs = require('fs');
const path = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const WEB = path.resolve(__dirname);
const SRC = path.resolve(WEB, 'src');
const DIST = path.resolve(WEB, 'dist');

const PY_BRIDGE = (() => {
  try {
    return fs.readFileSync(path.resolve(SRC, 'pyscript-bridge.raw'), 'utf8').trim();
  } catch (e) {
    console.warn('pyscript-bridge.raw missing; py block will be empty.');
    return '';
  }
})();

module.exports = {
  mode: process.env.NODE_ENV || 'production',
  entry: path.resolve(SRC, 'main.js'),

  output: {
    path: DIST,
    filename: 'app.js',
    clean: true,
  },

  module: {
    rules: [
      {
        test: /\.css$/i,
        use: [MiniCssExtractPlugin.loader, 'css-loader'],
      },
    ],
  },

  plugins: [
    new MiniCssExtractPlugin({ filename: 'style.css' }),
    new HtmlWebpackPlugin({
      template: path.resolve(SRC, 'index.html.ejs'),
      filename: 'index.html',
      inject: false,
      transform: (body) => body,
    }),
  ],

  devtool: false,

  resolve: {
    extensions: ['.js'],
    modules: [SRC, 'node_modules'],
  },

  optimization: {
    minimize: false,
  },
};
