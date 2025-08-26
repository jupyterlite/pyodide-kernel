// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';

import { PageConfig, URLExt } from '@jupyterlab/coreutils';

import { ILoggerRegistry, ILogPayload } from '@jupyterlab/logconsole';

import { IServiceWorkerManager } from '@jupyterlite/server';

import { IKernel, IKernelSpecs } from '@jupyterlite/kernel';

import KERNEL_ICON_SVG_STR from '../style/img/pyodide.svg';

export * as KERNEL_SETTINGS_SCHEMA from '../schema/kernel.v0.schema.json';

const KERNEL_ICON_URL = `data:image/svg+xml;base64,${btoa(KERNEL_ICON_SVG_STR)}`;

/**
 * The default CDN fallback for Pyodide
 */
const PYODIDE_CDN_URL = 'https://cdn.jsdelivr.net/pyodide/v0.28.2/full/pyodide.js';

/**
 * The id for the extension, and key in the litePlugins.
 */
const PLUGIN_ID = '@jupyterlite/pyodide-kernel-extension:kernel';

/**
 * A plugin to register the Pyodide kernel.
 */
const kernel: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  description: 'A plugin providing the Pyodide kernel.',
  autoStart: true,
  requires: [IKernelSpecs],
  optional: [IServiceWorkerManager, ILoggerRegistry],
  activate: (
    app: JupyterFrontEnd,
    kernelspecs: IKernelSpecs,
    serviceWorkerManager: IServiceWorkerManager | null,
    loggerRegistry: ILoggerRegistry | null,
  ) => {
    const { contents: contentsManager, sessions } = app.serviceManager;

    const config =
      JSON.parse(PageConfig.getOption('litePluginSettings') || '{}')[PLUGIN_ID] || {};

    const baseUrl = PageConfig.getBaseUrl();

    const url = config.pyodideUrl || PYODIDE_CDN_URL;

    const pyodideUrl = URLExt.parse(url).href;
    const pipliteWheelUrl = config.pipliteWheelUrl
      ? URLExt.parse(config.pipliteWheelUrl).href
      : undefined;
    const rawPipUrls = config.pipliteUrls || [];
    const pipliteUrls = rawPipUrls.map((pipUrl: string) => URLExt.parse(pipUrl).href);
    const disablePyPIFallback = !!config.disablePyPIFallback;
    const loadPyodideOptions = config.loadPyodideOptions || {};

    for (const [key, value] of Object.entries(loadPyodideOptions)) {
      if (key.endsWith('URL') && typeof value === 'string') {
        loadPyodideOptions[key] = new URL(value, baseUrl).href;
      }
    }

    // The logger will find the notebook associated with the kernel id
    // and log the payload to the log console for that notebook.
    const logger = async (options: { payload: ILogPayload; kernelId: string }) => {
      if (!loggerRegistry) {
        // nothing to do in this case
        return;
      }

      const { payload, kernelId } = options;

      // Find the session path that corresponds to the kernel ID
      let sessionPath = '';
      for (const session of sessions.running()) {
        if (session.kernel?.id === kernelId) {
          sessionPath = session.path;
          break;
        }
      }

      const logger = loggerRegistry.getLogger(sessionPath);
      logger.log(payload);
    };

    kernelspecs.register({
      spec: {
        name: 'python',
        display_name: 'Python (Pyodide)',
        language: 'python',
        argv: [],
        resources: {
          'logo-32x32': KERNEL_ICON_URL,
          'logo-64x64': KERNEL_ICON_URL,
        },
      },
      create: async (options: IKernel.IOptions): Promise<IKernel> => {
        const { PyodideKernel } = await import('@jupyterlite/pyodide-kernel');

        const mountDrive = !!(serviceWorkerManager?.enabled || crossOriginIsolated);

        const kernel = new PyodideKernel({
          ...options,
          pyodideUrl,
          pipliteWheelUrl,
          pipliteUrls,
          disablePyPIFallback,
          mountDrive,
          loadPyodideOptions,
          contentsManager,
          browsingContextId: serviceWorkerManager?.browsingContextId,
          logger,
        });

        if (mountDrive) {
          console.info('Pyodide contents will be synced with Jupyter Contents');
        } else {
          const warningMessage =
            'Pyodide contents will NOT be synced with Jupyter Contents. ' +
            'For full functionality, try using a regular browser tab instead of private/incognito mode, ' +
            'especially in Firefox where this is a known limitation.';
          console.warn(warningMessage);

          // Wait for kernel to be ready before logging the warning
          kernel.ready.then(() => {
            if (loggerRegistry) {
              void logger({
                payload: {
                  type: 'text',
                  data: warningMessage,
                  level: 'warning',
                },
                kernelId: options.id,
              });
            }
          });
        }

        return kernel;
      },
    });
  },
};

const plugins: JupyterFrontEndPlugin<any>[] = [kernel];

export default plugins;
