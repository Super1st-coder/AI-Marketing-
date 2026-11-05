import { App } from "vue";
import { createPinia } from "pinia";
import router from "@/router";
import vuetify from "./vuetify";
import i18n from "./i18n";
import { VueQueryPlugin, VueQueryPluginOptions } from "@tanstack/vue-query";

const vueQueryPluginOptions: VueQueryPluginOptions = {
  queryClientConfig: {
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  },
};

export function registerPlugins(app: App) {
  const pinia = createPinia();

  app.use(pinia);
  app.use(i18n);
  app.use(router);
  app.use(vuetify);
  app.use(VueQueryPlugin, vueQueryPluginOptions);
}
