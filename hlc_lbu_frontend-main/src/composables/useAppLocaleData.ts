import { appLocalesArray, defaultAppLocale } from "@/plugins/i18n";

export default function useAppLocaleData() {
  const { locale } = useI18n();

  const appLocale = computed(
    () =>
      appLocalesArray.find((appLocale) => locale.value === appLocale.code) ??
      defaultAppLocale,
  );

  return appLocale;
}
