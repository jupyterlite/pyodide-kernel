// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * Definitions for the Pyodide kernel.
 */

import type { Remote } from 'comlink';

import { IWorkerKernel } from '@jupyterlite/kernel';

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
}

/**
 * An convenience interface for Pyodide workers wrapped by a comlink Remote.
 */
export type IRemotePyodideWorkerKernel = Remote<IPyodideWorkerKernel>;

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
     * additional options to provide to `loadPyodide`
     * @see https://pyodide.org/en/stable/usage/api/js-api.html#globalThis.loadPyodide
     */
    loadPyodideOptions: Record<string, any> & {
      pyodideLockURL: string;
      packages: string[];
    };
  }
}
