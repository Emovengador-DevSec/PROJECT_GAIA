/// <reference types="vite/client" />
interface ImportMetaEnv {
  readonly VITE_CESIUM_ION_TOKEN?: string;
  readonly VITE_API_BASE?: string;
  readonly VITE_DATA_MODE?: "live" | "static";
}
