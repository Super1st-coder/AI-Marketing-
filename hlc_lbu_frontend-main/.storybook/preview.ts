import type { Preview } from "@storybook/vue3-vite";
import { setup } from "@storybook/vue3";
import "../src/styles/layers.css";
import "vuetify/styles/core";
import "../src/styles/main.css";
import vuetify from "../src/plugins/vuetify";
import i18n from "../src/plugins/i18n";
import { createPinia } from "pinia";
import router from "../src/router";
import AuthWrapper from "./AuthWrapper.vue";

const pinia = createPinia();
setup((app) => {
  app.use(pinia);
  app.use(router);
  app.use(i18n);
  app.use(vuetify);
});

const preview: Preview = {
  decorators: [
    (story) => ({
      components: { story, AuthWrapper },
      template: `
        <AuthWrapper>
          <story />
        </AuthWrapper>
      `,
    }),
  ],
  parameters: {
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
    options: {
      storySort: {
        order: [
          "Colors",
          ["All Colors"],
          "Components",
          [
            "Button",
            "CardBase",
            "Chip",
            "Alert",
            "Accordions",
            "PageTitle",
            "VideoTutorial",
            ["AccordionList"],
          ],
        ],
      },
    },
  },
};

export default preview;
