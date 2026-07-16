// Coincident v4
interface IMainOptions {
  transform?: any;
  encoder?: any;
  transfer?: boolean;
}

interface IMainReturn {
  Worker: typeof Worker & { proxy: typeof Proxy };
  native: boolean;
  transfer: any;
}

declare module 'coincident/main' {
  export default function coincident(options?: IMainOptions): IMainReturn;
}

interface IWorkerOptions extends IMainOptions {
  minByteLength?: number;
  maxByteLength?: number;
}

interface IWorkerReturn {
  proxy: any;
  native: boolean;
  transfer: any;
  ffi_timeout: number;
  sync: boolean;
}

declare module 'coincident/worker' {
  export default function coincident(options?: IWorkerOptions): Promise<IWorkerReturn>;
}
