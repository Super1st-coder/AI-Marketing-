<script setup lang="ts">
import { FormStepperStep } from "@/components/forms/multi-step/FormStepperBase.vue";
import { VideoProductionMode } from "@/services/funnel-flow/paid-social/VideoApi";
import {
  AdsAssemblyVideoScreenName,
  getVideoScreens,
} from "@/stores/funnel-flow/paid-social/FunnelPaidSocialAdsAssemblyStore";

const props = defineProps<{
  /**
   * Overrides the production mode of the generated scripts. Used by the
   * Settings step so the steps follow the mode picked in its form.
   */
  productionMode?: VideoProductionMode;
}>();

const store = useFunnelPaidSocialAdsAssemblyStore();
const { t } = useI18n();

const productionMode = computed(
  () =>
    props.productionMode ??
    store.currentAd?.draft.settings?.production_mode ??
    "FULL_VIDEO",
);

const screens = computed(() => {
  const settings = store.currentAd?.draft.settings;

  // The "Is the content ready?" choice only applies to the mode the scripts
  // were generated with
  return productionMode.value === settings?.production_mode
    ? store.currentVideoScreens
    : getVideoScreens(productionMode.value);
});

const labels = computed<Record<AdsAssemblyVideoScreenName, string>>(() => ({
  videoSettings: t("funnel-flow.paid-social.ads.video.stepper.settings"),
  videoScripts: t("funnel-flow.paid-social.ads.video.stepper.scripts"),
  videoStoryboard: t("funnel-flow.paid-social.ads.video.stepper.storyboard"),
  videoVoiceover: t("funnel-flow.paid-social.ads.video.stepper.voiceover"),
  videoAd: t("funnel-flow.paid-social.ads.video.stepper.ad"),
}));

// The steps after the furthest one reached are disabled: they are reached by
// moving forward, which is what generates what they need. "Completed" just
// reflects step order
const steps = computed<FormStepperStep[]>(() => {
  const currentIndex = store.currentScreen
    ? screens.value.indexOf(store.currentScreen as AdsAssemblyVideoScreenName)
    : -1;

  // The furthest step the ad reached, so going back to a previous step doesn't
  // disable the ones already done. Generating a step again moves it back, and
  // the steps after it are disabled again. It is never before the step shown
  const reachedIndex = Math.max(
    currentIndex,
    screens.value.indexOf(store.getVideoResumeScreen()),
  );

  return screens.value.map((screen, index) => ({
    label: labels.value[screen],
    completed: index < currentIndex,
    current: index === currentIndex,
    disabled: index > reachedIndex,
    onClick: async () => {
      // Like the sidebar, a step with unsaved changes asks before leaving
      if ((await useSaveLockingStore().execute()) === "cancel") return;

      store.setScreen(screen);
    },
  }));
});
</script>

<template>
  <FormStepperBase :data="steps" />
</template>
