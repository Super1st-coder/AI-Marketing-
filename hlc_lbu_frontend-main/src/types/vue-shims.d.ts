declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<{}, {}, any>;
  export default component;
}

declare module "import.meta" {
  interface ImportMetaEnv {
    readonly VITE_API_BASE_URL: string;
    readonly VITE_TOKEN_EXPIRY_BUFFER_SECONDS?: string;
    readonly VITE_SESSION_EXPIRY_BUFFER_SECONDS?: string;
    readonly VITE_SESSION_EXPIRY_WARNING_SECONDS?: string;
    readonly VITE_ENABLE_LUCA_GUIDE?: string;
    readonly VITE_ENABLE_BUDGET_STRATEGY?: string;
    readonly VITE_LUCA_GUIDE_API_BASE_URL: string;
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}
