<script setup lang="ts">
const store = useLucaGuideLayoutStore();
const { t } = useI18n();
const route = useRoute();

const steps = computed<FormStep[]>(() => [
  {
    name: "welcome",
    label: t("luca-guide.onboarding.steps.welcome"),
  },
  {
    name: "metaIntegration",
    label: t("luca-guide.onboarding.steps.meta-integration"),
  },
  {
    name: "northStarMetric",
    label: t("luca-guide.onboarding.steps.north-star-metric"),
  },
  {
    name: "classificationThresholds",
    label: t("luca-guide.onboarding.steps.classification-thresholds"),
  },
]);

const initialStep = computed(() => {
  if (route.query.fb === "connected" || route.query.fb === "error") {
    return "metaIntegration";
  }

  return steps.value[store.completedOnboardingSteps]?.name ?? "welcome";
});

const { currentFlatStepIndex } = useMultiStepForm(steps, {
  initialStep,
  useLocalStorage: false,
  lastCompletedFlatStepIndex: () => store.completedOnboardingSteps,
});

watch(
  currentFlatStepIndex,
  (index) => {
    if (!store.isOnboardingCompleted) {
      // Sidebar shows completed count (= current index while a step is in progress)
      store.completedOnboardingSteps = Math.max(
        store.completedOnboardingSteps,
        index,
      );
    }
  },
  { immediate: true },
);
</script>

<template>
  <FormStep name="welcome">
    <LucaGuideOnboardingWelcome />
  </FormStep>

  <FormStep name="metaIntegration">
    <LucaGuideOnboardingMetaIntegration />
  </FormStep>

  <FormStep name="northStarMetric">
    <LucaGuideOnboardingNorthStarMetric />
  </FormStep>

  <FormStep name="classificationThresholds">
    <LucaGuideOnboardingClassificationThresholds />
  </FormStep>
</template>
