// Copyright (c) Jupyter Development Team.
// Distributed under the terms of the Modified BSD License.

/**
 * A WebWorker entrypoint that uses coincident to handle postMessage details
 */
import coincident from 'coincident';

import { PyodideRemoteKernel } from './worker';
import { IPyodideWorkerKernel } from './tokens';

const worker = new PyodideRemoteKernel();

const workerAPI: IPyodideWorkerKernel = coincident(self) as IPyodideWorkerKernel;

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
