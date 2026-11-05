<script setup lang="ts">
const store = useLucaGuideLayoutStore();
const router = useRouter();
const { t } = useI18n();

usePageTitle(() =>
  t("routes.luca-guide-onboarding", { brand: store.brand?.name ?? "" }),
);

if (store.isOnboardingCompleted) {
  await router.replace({ name: "LucaGuide" });
}
</script>

<template>
  <LucaGuideOnboarding />
</template>
