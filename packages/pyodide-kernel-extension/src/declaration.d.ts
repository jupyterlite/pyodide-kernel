// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

declare module '../schema/*.json' {
  const res: string;
  export default res;
}

declare module '!!url-loader!*' {
  const res: string;
  export default res;
}
