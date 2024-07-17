// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * A WebWorker entrypoint that uses coincident to handle postMessage details
 */
import coincident from 'coincident';

import {
  ContentsAPI,
  DriveFS,
  ServiceWorkerContentsAPI,
  TDriveMethod,
  TDriveRequest,
  TDriveResponse,
} from '@jupyterlite/contents';

import { PyodideRemoteKernel } from './worker';
import { IPyodideWorkerKernel } from './tokens';

const workerAPI = coincident(self) as IPyodideWorkerKernel;

/**
 * An Emscripten-compatible synchronous Contents API using shared array buffers.
 */
export class SharedBufferContentsAPI extends ContentsAPI {
  request<T extends TDriveMethod>(data: TDriveRequest<T>): TDriveResponse<T> {
    return workerAPI.processDriveRequest(data);
  }
}

/**
 * A custom drive implementation which uses shared array buffers if available, service worker otherwise
 */
class PyodideDriveFS extends DriveFS {
  createAPI(options: DriveFS.IOptions): ContentsAPI {
    if (crossOriginIsolated) {
      return new SharedBufferContentsAPI(
        options.driveName,
        options.mountpoint,
        options.FS,
        options.ERRNO_CODES,
      );
    } else {
      return new ServiceWorkerContentsAPI(
        options.baseUrl,
        options.driveName,
        options.mountpoint,
        options.FS,
        options.ERRNO_CODES,
      );
    }
  }
}

export class PyodideCoincidentKernel extends PyodideRemoteKernel {
  /**
   * Setup custom Emscripten FileSystem
   */
  protected async initFilesystem(
    options: IPyodideWorkerKernel.IOptions,
  ): Promise<void> {
    if (options.mountDrive) {
      const mountpoint = '/drive';
      const { FS, PATH, ERRNO_CODES } = this._pyodide;
      const { baseUrl } = options;

      const driveFS = new PyodideDriveFS({
        FS,
        PATH,
        ERRNO_CODES,
        baseUrl,
        driveName: this._driveName,
        mountpoint,
      });
      FS.mkdir(mountpoint);
      FS.mount(driveFS, {}, mountpoint);
      FS.chdir(mountpoint);
      this._driveFS = driveFS;
    }
  }
}

const sendWorkerMessage = workerAPI.processWorkerMessage.bind(workerAPI);
const worker = new PyodideCoincidentKernel(sendWorkerMessage);

workerAPI.initialize = worker.initialize.bind(worker);
workerAPI.execute = worker.execute.bind(worker);
workerAPI.complete = worker.complete.bind(worker);
workerAPI.inspect = worker.inspect.bind(worker);
workerAPI.isComplete = worker.isComplete.bind(worker);
workerAPI.commInfo = worker.commInfo.bind(worker);
workerAPI.commOpen = worker.commOpen.bind(worker);
workerAPI.commMsg = worker.commMsg.bind(worker);
workerAPI.commClose = worker.commClose.bind(worker);
workerAPI.inputReply = worker.inputReply.bind(worker);
