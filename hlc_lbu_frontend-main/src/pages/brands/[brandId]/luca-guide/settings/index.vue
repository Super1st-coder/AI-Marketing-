<script setup lang="ts">
const store = useLucaGuideLayoutStore();
const { t } = useI18n();

usePageTitle(() =>
  t("routes.luca-guide-settings", { brand: store.brand?.name ?? "" }),
);
</script>

<template>
  <LucaGuideOnboarding />
</template>
