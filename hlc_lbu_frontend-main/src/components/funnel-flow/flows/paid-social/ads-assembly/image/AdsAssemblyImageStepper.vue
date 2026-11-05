<script setup lang="ts">
const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();

const steps = computed(() => [
  {
    label: t("funnel-flow.paid-social.ads.stepper.asset-origin"),
    completed:
      store.currentScreen === "settings" || store.currentScreen === "refine",
    current: store.currentScreen === "assetOrigin",
    disabled: false,
    onClick: () => {
      store.setScreen("assetOrigin");
    },
  },
  {
    label: t("funnel-flow.paid-social.ads.stepper.settings"),
    completed: store.currentScreen === "refine",
    current: store.currentScreen === "settings",
    disabled: !store.currentSet?.media_platform_project_id,
    onClick: () => {
      store.setScreen("settings");
    },
  },
  {
    label: t("funnel-flow.paid-social.ads.stepper.select-refine"),
    completed: false,
    current: store.currentScreen === "refine",
    // Never disabled while it's the current step (e.g. when entering it
    // through the manual mode, before any variant exists)
    disabled:
      store.currentScreen !== "refine" &&
      (!store.currentSet?.media_platform_project_id ||
        !store.doesCurrentAdSetHaveGeneratedVariants),
    onClick: () => {
      store.setScreen("refine");
    },
  },
]);
</script>

<template>
  <FormStepperBase :data="steps" />
</template>
