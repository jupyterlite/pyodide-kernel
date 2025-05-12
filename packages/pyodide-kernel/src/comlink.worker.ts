// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * A WebWorker entrypoint that uses comlink to handle postMessage details
 */

import { expose } from 'comlink';

import { URLExt } from '@jupyterlab/coreutils';

import { KernelMessage } from '@jupyterlab/services';

import { DriveFS } from '@jupyterlite/contents';

import { IPyodideWorkerKernel } from './tokens';

import { PyodideRemoteKernel } from './worker';

export class PyodideComlinkKernel extends PyodideRemoteKernel {
  constructor() {
    super();
    // use postMessage, but in a format, that comlink would not process.
    this._sendWorkerMessage = (msg: any) => {
      postMessage({ _kernelMessage: msg });
    };
    this._logMessage = (msg: any) => {
      postMessage({ _logMessage: msg });
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
      const { baseUrl, browsingContextId } = options;

      const driveFS = new DriveFS({
        FS: FS as any,
        PATH,
        ERRNO_CODES,
        baseUrl,
        driveName: this._driveName,
        mountpoint,
        browsingContextId,
      });
      FS.mkdirTree(mountpoint);
      FS.mount(driveFS, {}, mountpoint);
      FS.chdir(mountpoint);
      this._driveFS = driveFS;
    }
  }

  /**
   * Send input request and receive input reply via service worker.
   */
  protected sendInputRequest(prompt: string, password: boolean): string | undefined {
    const parentHeader = this.formatResult(this._kernel._parent_header)['header'];

    // Filling out the input_request message fields based on jupyterlite BaseKernet.inputRequest
    const inputRequest = KernelMessage.createMessage<KernelMessage.IInputRequestMsg>({
      channel: 'stdin',
      msgType: 'input_request',
      session: parentHeader?.session ?? '',
      parentHeader: parentHeader,
      content: {
        prompt,
        password,
      },
    });

    try {
      if (!this._options) {
        throw new Error('Kernel options not set');
      }

      const { baseUrl, browsingContextId } = this._options;
      if (!browsingContextId) {
        throw new Error('Kernel browsingContextId not set');
      }

      const xhr = new XMLHttpRequest();
      const url = URLExt.join(baseUrl, '/api/stdin/kernel');
      xhr.open('POST', url, false); // Synchronous XMLHttpRequest
      const msg = JSON.stringify({
        browsingContextId,
        data: inputRequest,
      });
      // Send input request, this blocks until the input reply is received.
      xhr.send(msg);
      const inputReply = JSON.parse(xhr.response as string);

      if ('error' in inputReply) {
        // Service worker may return an error instead of an input reply message.
        throw new Error(inputReply['error']);
      }

      return inputReply.content?.value;
    } catch (err) {
      console.warn(`Failed to request stdin via service worker: ${err}`);
      return undefined;
    }
  }
}

const worker = new PyodideComlinkKernel();

expose(worker);
