import {
  JupyterLiteServer,
  JupyterLiteServerPlugin
} from '@jupyterlite/server';

/**
 * Initialization data for the @jupyterlite/pyodide-kernel extension.
 */
const plugin: JupyterLiteServerPlugin<void> = {
  id: '@jupyterlite/pyodide-kernel:plugin',
  autoStart: true,
  activate: (app: JupyterLiteServer) => {
    console.log(
      'JupyterLite server extension @jupyterlite/pyodide-kernel is activated!'
    );
  }
};

export default plugin;
