// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * Definitions for the Pyodide kernel.
 */

import {
  TDriveMethod,
  TDriveRequest,
  TDriveResponse,
  IWorkerKernel,
} from '@jupyterlite/services';

/**
 * The schema for a Warehouse-like index, as used by piplite.
 */
export * as PIPLITE_INDEX_SCHEMA from '../schema/piplite.v0.schema.json';

/**
 * An interface for Pyodide workers.
 */
export interface IPyodideWorkerKernel extends IWorkerKernel {
  /**
   * Handle any lazy initialization activities.
   */
  initialize(options: IPyodideWorkerKernel.IOptions): Promise<void>;

  /**
   * Process drive request
   * @param data
   */
  processDriveRequest<T extends TDriveMethod>(
    data: TDriveRequest<T>,
  ): TDriveResponse<T>;
}

/**
 * An interface for Pyodide workers that use comlink.
 */
export interface IComlinkPyodideKernel extends IPyodideWorkerKernel {
  /**
   * Register a callback for handling messages from the worker.
   */
  registerWorkerMessageCallback(callback: (msg: any) => void): void;

  /**
   * Register a callback for handling log messages from the worker.
   */
  registerLogMessageCallback(callback: (msg: any) => void): void;
}

/**
 * An interface for Coincident Pyodide workers that include extra SharedArrayBuffer
 * functionality.
 */
export interface ICoincidentPyodideWorkerKernel extends IPyodideWorkerKernel {
  /**
   * Process a log message
   * @param msg
   */
  processLogMessage(msg: any): void;

  /**
   * Process worker message
   * @param msg
   */
  processWorkerMessage(msg: any): void;
  /**
   * Process stdin request, blocking until the reply is received.
   * This is sync for the web worker, async for the UI thread.
   * @param inputRequest
   */
  processStdinRequest(content: {
    prompt: string;
    password: boolean;
  }): string | undefined;
}

/**
 * Deprecated.
 */
export type IRemotePyodideWorkerKernel = IPyodideWorkerKernel;

/**
 * An namespace for Pyodide workers.
 */
export namespace IPyodideWorkerKernel {
  /**
   * Initialization options for a worker.
   */
  export interface IOptions extends IWorkerKernel.IOptions {
    /**
     * The URL of the main `pyodide.js` file in the standard pyodide layout.
     */
    pyodideUrl: string;

    /**
     * The URL of a pyodide index file in the standard pyodide layout.
     */
    indexUrl: string;

    /**
     * The URL of the `piplite` wheel for bootstrapping.
     */
    pipliteWheelUrl: string;

    /**
     * The URLs of additional warehouse-like wheel listings.
     */
    pipliteUrls: string[];

    /**
     * Whether `piplite` should fall back to the hard-coded `pypi.org` for resolving packages.
     */
    disablePyPIFallback: boolean;

    /**
     * The current working directory in which to start the kernel.
     */
    location: string;

    /**
     * Whether or not to mount the Emscripten drive
     */
    mountDrive: boolean;

    /**
     * A unique ID to identify the origin of this request.
     * This should be provided by `IServiceWorkerManager` and is used to
     * identify the browsing context from which the request originated.
     */
    browsingContextId?: string;

    /**
     * additional options to provide to `loadPyodide`
     * @see https://pyodide.org/en/stable/usage/api/js-api.html#globalThis.loadPyodide
     */
    loadPyodideOptions: Record<string, any> & {
      lockFileURL: string;
      packages: string[];
    };

    /**
     * The kernel id.
     */
    kernelId?: string;
  }
}
