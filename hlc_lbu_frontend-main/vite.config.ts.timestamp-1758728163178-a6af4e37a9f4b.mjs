// vite.config.ts
import { defineConfig } from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
import Vuetify from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/vite-plugin-vuetify/dist/index.mjs";
import path from "path";
import Components from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/unplugin-vue-components/dist/vite.js";
import AutoImport from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/unplugin-auto-import/dist/vite.js";
import {
  VueUseComponentsResolver,
  VueUseDirectiveResolver
} from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/unplugin-vue-components/dist/resolvers.js";
import VueI18nPlugin from "file:///C:/Desarrollo/Proyectos%20Ramon%20Valera/newdevelop/hlc_lbu_frontend/node_modules/@intlify/unplugin-vue-i18n/lib/vite.mjs";
var __vite_injected_original_dirname = "C:\\Desarrollo\\Proyectos Ramon Valera\\newdevelop\\hlc_lbu_frontend";
var vite_config_default = defineConfig({
  plugins: [
    vue(),
    VueI18nPlugin({
      include: [path.resolve(__vite_injected_original_dirname, "./src/plugins/i18n/locales/**")]
    }),
    Vuetify(),
    Components({
      types: [
        {
          from: "@iconify/vue",
          names: ["Icon"]
        }
      ],
      resolvers: [
        VueUseComponentsResolver(),
        VueUseDirectiveResolver(),
        (name) => {
          if (name === "Icon") return { name, from: "@iconify/vue" };
        }
      ]
    }),
    AutoImport({
      imports: [
        "vue",
        "@vueuse/core",
        "@vueuse/math",
        "vue-i18n",
        "pinia",
        "vee-validate",
        "vue-router"
      ],
      dirs: [
        {
          glob: "./src/utils/**",
          types: true
        },
        {
          glob: "./src/stores/**",
          types: true
        },
        {
          glob: "./src/composables/**",
          types: true
        },
        {
          glob: "./src/types/**",
          types: true
        }
      ],
      vueTemplate: true,
      viteOptimizeDeps: true,
      dirsScanOptions: {
        types: true
      }
    })
  ],
  resolve: {
    alias: {
      "@": path.resolve(__vite_injected_original_dirname, "./src"),
      "@core": path.resolve(__vite_injected_original_dirname, "./src/@core")
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJDOlxcXFxEZXNhcnJvbGxvXFxcXFByb3llY3RvcyBSYW1vbiBWYWxlcmFcXFxcbmV3ZGV2ZWxvcFxcXFxobGNfbGJ1X2Zyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJDOlxcXFxEZXNhcnJvbGxvXFxcXFByb3llY3RvcyBSYW1vbiBWYWxlcmFcXFxcbmV3ZGV2ZWxvcFxcXFxobGNfbGJ1X2Zyb250ZW5kXFxcXHZpdGUuY29uZmlnLnRzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9DOi9EZXNhcnJvbGxvL1Byb3llY3RvcyUyMFJhbW9uJTIwVmFsZXJhL25ld2RldmVsb3AvaGxjX2xidV9mcm9udGVuZC92aXRlLmNvbmZpZy50c1wiOy8vIHZpdGUuY29uZmlnLnRzICh1c2luZyBUeXBlU2NyaXB0KVxyXG5pbXBvcnQgeyBkZWZpbmVDb25maWcgfSBmcm9tIFwidml0ZVwiO1xyXG5pbXBvcnQgdnVlIGZyb20gXCJAdml0ZWpzL3BsdWdpbi12dWVcIjtcclxuaW1wb3J0IFZ1ZXRpZnkgZnJvbSBcInZpdGUtcGx1Z2luLXZ1ZXRpZnlcIjtcclxuaW1wb3J0IHBhdGggZnJvbSBcInBhdGhcIjtcclxuaW1wb3J0IENvbXBvbmVudHMgZnJvbSBcInVucGx1Z2luLXZ1ZS1jb21wb25lbnRzL3ZpdGVcIjtcclxuaW1wb3J0IEF1dG9JbXBvcnQgZnJvbSBcInVucGx1Z2luLWF1dG8taW1wb3J0L3ZpdGVcIjtcclxuaW1wb3J0IHtcclxuICBWdWVVc2VDb21wb25lbnRzUmVzb2x2ZXIsXHJcbiAgVnVlVXNlRGlyZWN0aXZlUmVzb2x2ZXIsXHJcbn0gZnJvbSBcInVucGx1Z2luLXZ1ZS1jb21wb25lbnRzL3Jlc29sdmVyc1wiO1xyXG5pbXBvcnQgVnVlSTE4blBsdWdpbiBmcm9tIFwiQGludGxpZnkvdW5wbHVnaW4tdnVlLWkxOG4vdml0ZVwiO1xyXG5cclxuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKHtcclxuICBwbHVnaW5zOiBbXHJcbiAgICB2dWUoKSxcclxuICAgIFZ1ZUkxOG5QbHVnaW4oe1xyXG4gICAgICBpbmNsdWRlOiBbcGF0aC5yZXNvbHZlKF9fZGlybmFtZSwgXCIuL3NyYy9wbHVnaW5zL2kxOG4vbG9jYWxlcy8qKlwiKV0sXHJcbiAgICB9KSxcclxuICAgIFZ1ZXRpZnkoKSxcclxuICAgIENvbXBvbmVudHMoe1xyXG4gICAgICB0eXBlczogW1xyXG4gICAgICAgIHtcclxuICAgICAgICAgIGZyb206IFwiQGljb25pZnkvdnVlXCIsXHJcbiAgICAgICAgICBuYW1lczogW1wiSWNvblwiXSxcclxuICAgICAgICB9LFxyXG4gICAgICBdLFxyXG4gICAgICByZXNvbHZlcnM6IFtcclxuICAgICAgICBWdWVVc2VDb21wb25lbnRzUmVzb2x2ZXIoKSxcclxuICAgICAgICBWdWVVc2VEaXJlY3RpdmVSZXNvbHZlcigpLFxyXG4gICAgICAgIChuYW1lKSA9PiB7XHJcbiAgICAgICAgICBpZiAobmFtZSA9PT0gXCJJY29uXCIpIHJldHVybiB7IG5hbWUsIGZyb206IFwiQGljb25pZnkvdnVlXCIgfTtcclxuICAgICAgICB9LFxyXG4gICAgICBdLFxyXG4gICAgfSksXHJcbiAgICBBdXRvSW1wb3J0KHtcclxuICAgICAgaW1wb3J0czogW1xyXG4gICAgICAgIFwidnVlXCIsXHJcbiAgICAgICAgXCJAdnVldXNlL2NvcmVcIixcclxuICAgICAgICBcIkB2dWV1c2UvbWF0aFwiLFxyXG4gICAgICAgIFwidnVlLWkxOG5cIixcclxuICAgICAgICBcInBpbmlhXCIsXHJcbiAgICAgICAgXCJ2ZWUtdmFsaWRhdGVcIixcclxuICAgICAgICBcInZ1ZS1yb3V0ZXJcIixcclxuICAgICAgXSxcclxuICAgICAgZGlyczogW1xyXG4gICAgICAgIHtcclxuICAgICAgICAgIGdsb2I6IFwiLi9zcmMvdXRpbHMvKipcIixcclxuICAgICAgICAgIHR5cGVzOiB0cnVlLFxyXG4gICAgICAgIH0sXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgZ2xvYjogXCIuL3NyYy9zdG9yZXMvKipcIixcclxuICAgICAgICAgIHR5cGVzOiB0cnVlLFxyXG4gICAgICAgIH0sXHJcbiAgICAgICAge1xyXG4gICAgICAgICAgZ2xvYjogXCIuL3NyYy9jb21wb3NhYmxlcy8qKlwiLFxyXG4gICAgICAgICAgdHlwZXM6IHRydWUsXHJcbiAgICAgICAgfSxcclxuICAgICAgICB7XHJcbiAgICAgICAgICBnbG9iOiBcIi4vc3JjL3R5cGVzLyoqXCIsXHJcbiAgICAgICAgICB0eXBlczogdHJ1ZSxcclxuICAgICAgICB9LFxyXG4gICAgICBdLFxyXG4gICAgICB2dWVUZW1wbGF0ZTogdHJ1ZSxcclxuICAgICAgdml0ZU9wdGltaXplRGVwczogdHJ1ZSxcclxuICAgICAgZGlyc1NjYW5PcHRpb25zOiB7XHJcbiAgICAgICAgdHlwZXM6IHRydWUsXHJcbiAgICAgIH0sXHJcbiAgICB9KSxcclxuICBdLFxyXG4gIHJlc29sdmU6IHtcclxuICAgIGFsaWFzOiB7XHJcbiAgICAgIFwiQFwiOiBwYXRoLnJlc29sdmUoX19kaXJuYW1lLCBcIi4vc3JjXCIpLFxyXG4gICAgICBcIkBjb3JlXCI6IHBhdGgucmVzb2x2ZShfX2Rpcm5hbWUsIFwiLi9zcmMvQGNvcmVcIiksXHJcbiAgICB9LFxyXG4gIH0sXHJcbn0pO1xyXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQ0EsU0FBUyxvQkFBb0I7QUFDN0IsT0FBTyxTQUFTO0FBQ2hCLE9BQU8sYUFBYTtBQUNwQixPQUFPLFVBQVU7QUFDakIsT0FBTyxnQkFBZ0I7QUFDdkIsT0FBTyxnQkFBZ0I7QUFDdkI7QUFBQSxFQUNFO0FBQUEsRUFDQTtBQUFBLE9BQ0s7QUFDUCxPQUFPLG1CQUFtQjtBQVgxQixJQUFNLG1DQUFtQztBQWF6QyxJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTO0FBQUEsSUFDUCxJQUFJO0FBQUEsSUFDSixjQUFjO0FBQUEsTUFDWixTQUFTLENBQUMsS0FBSyxRQUFRLGtDQUFXLCtCQUErQixDQUFDO0FBQUEsSUFDcEUsQ0FBQztBQUFBLElBQ0QsUUFBUTtBQUFBLElBQ1IsV0FBVztBQUFBLE1BQ1QsT0FBTztBQUFBLFFBQ0w7QUFBQSxVQUNFLE1BQU07QUFBQSxVQUNOLE9BQU8sQ0FBQyxNQUFNO0FBQUEsUUFDaEI7QUFBQSxNQUNGO0FBQUEsTUFDQSxXQUFXO0FBQUEsUUFDVCx5QkFBeUI7QUFBQSxRQUN6Qix3QkFBd0I7QUFBQSxRQUN4QixDQUFDLFNBQVM7QUFDUixjQUFJLFNBQVMsT0FBUSxRQUFPLEVBQUUsTUFBTSxNQUFNLGVBQWU7QUFBQSxRQUMzRDtBQUFBLE1BQ0Y7QUFBQSxJQUNGLENBQUM7QUFBQSxJQUNELFdBQVc7QUFBQSxNQUNULFNBQVM7QUFBQSxRQUNQO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsUUFDQTtBQUFBLFFBQ0E7QUFBQSxRQUNBO0FBQUEsTUFDRjtBQUFBLE1BQ0EsTUFBTTtBQUFBLFFBQ0o7QUFBQSxVQUNFLE1BQU07QUFBQSxVQUNOLE9BQU87QUFBQSxRQUNUO0FBQUEsUUFDQTtBQUFBLFVBQ0UsTUFBTTtBQUFBLFVBQ04sT0FBTztBQUFBLFFBQ1Q7QUFBQSxRQUNBO0FBQUEsVUFDRSxNQUFNO0FBQUEsVUFDTixPQUFPO0FBQUEsUUFDVDtBQUFBLFFBQ0E7QUFBQSxVQUNFLE1BQU07QUFBQSxVQUNOLE9BQU87QUFBQSxRQUNUO0FBQUEsTUFDRjtBQUFBLE1BQ0EsYUFBYTtBQUFBLE1BQ2Isa0JBQWtCO0FBQUEsTUFDbEIsaUJBQWlCO0FBQUEsUUFDZixPQUFPO0FBQUEsTUFDVDtBQUFBLElBQ0YsQ0FBQztBQUFBLEVBQ0g7QUFBQSxFQUNBLFNBQVM7QUFBQSxJQUNQLE9BQU87QUFBQSxNQUNMLEtBQUssS0FBSyxRQUFRLGtDQUFXLE9BQU87QUFBQSxNQUNwQyxTQUFTLEtBQUssUUFBUSxrQ0FBVyxhQUFhO0FBQUEsSUFDaEQ7QUFBQSxFQUNGO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
