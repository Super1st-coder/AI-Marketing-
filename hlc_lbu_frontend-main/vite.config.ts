// vite.config.ts (using TypeScript)
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";
import Vuetify from "vite-plugin-vuetify";
import path from "path";
import Components from "unplugin-vue-components/vite";
import AutoImport from "unplugin-auto-import/vite";
import {
  VueUseComponentsResolver,
  VueUseDirectiveResolver,
} from "unplugin-vue-components/resolvers";
import VueI18nPlugin from "@intlify/unplugin-vue-i18n/vite";

export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
    VueI18nPlugin({}),
    Vuetify(),
    Components({
      types: [
        {
          from: "@iconify/vue",
          names: ["Icon"],
        },
      ],
      resolvers: [
        VueUseComponentsResolver(),
        VueUseDirectiveResolver(),
        (name) => {
          if (name === "Icon") return { name, from: "@iconify/vue" };
        },
      ],
    }),
    AutoImport({
      imports: [
        "vue",
        "@vueuse/core",
        "@vueuse/math",
        "vue-i18n",
        "pinia",
        "vee-validate",
        "vue-router",
      ],
      dirs: [
        {
          glob: "./src/constants/**",
          types: true,
        },
        {
          glob: "./src/utils/**",
          types: true,
        },
        {
          glob: "./src/stores/**",
          types: true,
        },
        {
          glob: "./src/composables/**",
          types: true,
        },
        {
          glob: "./src/types/**",
          types: true,
        },
      ],
      vueTemplate: true,
      viteOptimizeDeps: true,
      dirsScanOptions: {
        types: true,
      },
    }),
  ],
  resolve: {
    dedupe: ["universal-cookie"],
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@core": path.resolve(__dirname, "./src/@core"),
    },
  },
});
