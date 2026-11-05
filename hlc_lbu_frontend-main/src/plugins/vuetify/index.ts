import { createVuetify } from "vuetify";
import defaults from "./defaults";
import themes from "./theme";
import { aliases, mdi } from "vuetify/iconsets/mdi";
import "@mdi/font/css/materialdesignicons.css";

export default createVuetify({
  theme: {
    defaultTheme: "light",
    utilities: false,
    themes,
  },
  display: {
    mobileBreakpoint: "md",
    thresholds: {
      xs: 0,
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
      xxl: 1536, // Tailwind 2xl
    },
  },
  icons: {
    defaultSet: "mdi",
    aliases,
    sets: { mdi },
  },
  defaults,
});
