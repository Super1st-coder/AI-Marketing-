import { createApp } from "vue";
import "./styles/layers.css";
import "vuetify/styles/core";
import "./styles/main.css";
import App from "./App.vue";

import { registerPlugins } from "./plugins";
import { registerCustomIconifyIcons } from "./icons";
import router from "./router";

async function bootstrap() {
  const app = createApp(App);

  registerPlugins(app);
  registerCustomIconifyIcons();

  // Wait for the initial navigation (including lazy locale load) before mount
  await router.isReady();

  app.mount("#app");
}

bootstrap();
