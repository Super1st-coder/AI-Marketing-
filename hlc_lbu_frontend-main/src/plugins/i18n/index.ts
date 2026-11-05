import { nextTick } from "vue";
import { createI18n } from "vue-i18n";
import type { Locale } from "vue-i18n";

export type AppLocaleData = {
  name: string;
  code: string;
  apiName: string;
};

export const appLocales: Record<string, AppLocaleData> = {
  en: {
    name: "English",
    code: "en",
    apiName: "English",
  },
  es: {
    name: "Español",
    code: "es",
    apiName: "Spanish",
  },
};

export const SUPPORT_LOCALES = Object.keys(appLocales);

export const appLocalesArray = Object.entries(appLocales).map(
  ([_code, locale]) => locale,
);

export const defaultLocaleCode = "en";
export const defaultAppLocale = appLocales[defaultLocaleCode];

const i18n = createI18n({
  legacy: false,
  locale: defaultLocaleCode,
  fallbackLocale: defaultLocaleCode,
  messages: {},
  globalInjection: true,
});

export function setI18nLanguage(locale: Locale) {
  i18n.global.locale.value = locale;
  document.querySelector("html")!.setAttribute("lang", locale);
}

export async function loadLocaleMessages(locale: Locale) {
  // load locale messages with dynamic import
  // https://vue-i18n.intlify.dev/guide/advanced/lazy
  const messages = await import(`./locales/${locale}.json`);

  // set locale and locale message
  i18n.global.setLocaleMessage(locale, messages.default);

  return nextTick();
}

export default i18n;
