export function usePageTitle(title?: MaybeRefOrGetter<string>) {
  const { t } = useI18n();

  const finalTitle = computed(() =>
    title ? t("routes.template", { route: toValue(title) }) : t("routes.title"),
  );

  // Disable restoreOnUnmount: Vue mounts the new route before unmounting the old
  // one, so the leaving page would otherwise overwrite the new title on unmount.
  useTitle(finalTitle, { restoreOnUnmount: false });
}
