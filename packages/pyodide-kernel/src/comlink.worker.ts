// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * A WebWorker entrypoint that uses comlink to handle postMessage details
 */

import { expose } from 'comlink';

import { DriveFS } from '@jupyterlite/contents';

import { IPyodideWorkerKernel } from './tokens';

import { PyodideRemoteKernel } from './worker';

export class PyodideComlinkKernel extends PyodideRemoteKernel {
  constructor() {
    super();
    this._sendWorkerMessage = (msg: any) => {
      // use postMessage, but in a format, that comlink would not process.
      postMessage({ _kernelMessage: msg });
    };
  }

  /**
   * Setup custom Emscripten FileSystem
   */
  protected async initFilesystem(
    options: IPyodideWorkerKernel.IOptions,
  ): Promise<void> {
    if (options.mountDrive) {
      const mountpoint = '/drive';
      const { FS, PATH, ERRNO_CODES } = this._pyodide;
      const { baseUrl, tabId } = options;

      // This uses the ServiceWorkerContentsAPI by default
      const driveFS = new DriveFS({
        FS: FS as any,
        PATH,
        ERRNO_CODES,
        baseUrl,
        tabId,
        driveName: this._driveName,
        mountpoint,
      });
      FS.mkdirTree(mountpoint);
      FS.mount(driveFS, {}, mountpoint);
      FS.chdir(mountpoint);
      this._driveFS = driveFS;
    }
  }
}

const worker = new PyodideComlinkKernel();

expose(worker);
