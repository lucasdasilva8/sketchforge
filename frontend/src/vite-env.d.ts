/// <reference types="vite/client" />

interface Window {
  SKETCHFORGE_API?: string;
}

declare module "replicad-opencascadejs/src/replicad_single.js" {
  import type { OpenCascadeInstance } from "replicad-opencascadejs";
  interface OpenCascadeModule {
    (config?: { locateFile?: (path: string) => string }): Promise<OpenCascadeInstance>;
    ready: Promise<OpenCascadeInstance>;
  }
  const opencascade: OpenCascadeModule;
  export default opencascade;
}
