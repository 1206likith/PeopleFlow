/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_WS_BASE_URL?: string;
  readonly VITE_DEFAULT_ACTOR_ID?: string;
  readonly VITE_ENABLE_UNITY_HOOK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
