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
 * The schema for a pyodide-compatible repodata.
 */
export * as REPODATA_INDEX_SCHEMA from '../schema/repodata.v0.schema.json';

/**
 * The schema for a ``package.json` that might impact pyodide-kernel.
 */
export * as PKG_JSON_PYODIDE_KERNEL_SCHEMA from '../schema/package.v0.schema.json';

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
     * The URLs of additional pyodide repodata.json files
     */
    repodataUrls: string[];

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
  }

  /**
   * Data about a single version of a package.
   */
  export interface IRepoDataPackage {
    /**
     * A list of PEP 503 names for packages.
     */
    depends: string[];
    /**
     * The relative or full-qualified URL for the package to install.
     */
    file_name: string;
    /**
     * Importable modules which should trigger installation of this package.
     */
    imports: string[];
    /**
     * The destination for this package: ``dynlib`` is not yet fully understood.
     */
    install_dir: 'site' | 'dynlib';
    /**
     * The PEP 503 name of the package.
     */
    name: string;
    /**
     * A SHA256 digest for the ``file_name``.
     */
    sha256: string;
    /**
     * The version of this package.
     */
    version: string;
  }

  export interface IRepoData {
    /**
     * Metadata about this repodata.
     *
     * This is not currently used.
     */
    info?: {
      arch: string;
      platform: string;
      python: string;
      version: string;
    };
    /**
     * A dictionary of packages, keyed by PEP 503 name.
     */
    packages: {
      [key: string]: IRepoDataPackage;
    };
  }
}
