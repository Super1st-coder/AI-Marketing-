<script setup lang="ts">
import type {
  LucaGuideCampaign,
  LucaGuideCampaignContext,
} from "@/services/guide/LucaGuideCampaignsApi";

export type LucaGuideCampaignOnboardingFormData = {
  campaign: LucaGuideCampaign;
  context: LucaGuideCampaignContext | null;
};

const props = defineProps<{
  campaign: LucaGuideCampaign;
  context: LucaGuideCampaignContext | null;
}>();

const { t } = useI18n();

const createdFromBuilder = computed(
  () => props.context?.created_from_builder === true,
);

const hasFullContext = computed(
  () => props.context?.context_status === "FULL_CONTEXT",
);

const steps = computed<FormStep[]>(() => {
  if (createdFromBuilder.value) {
    return [
      {
        name: "brief",
        label: t("luca-guide.campaigns.onboarding.steps.brief"),
      },
      {
        name: "creativeStrategyProposals",
        label: t(
          "luca-guide.campaigns.onboarding.steps.creative-strategy-proposals",
        ),
      },
      {
        name: "metricsNorthStar",
        label: t("luca-guide.campaigns.onboarding.steps.metrics-north-star"),
      },
    ];
  }

  return [
    {
      name: "context",
      label: t("luca-guide.campaigns.onboarding.steps.context"),
    },
    {
      name: "metricsNorthStar",
      label: t("luca-guide.campaigns.onboarding.steps.metrics-north-star"),
    },
  ];
});

useMultiStepForm<LucaGuideCampaignOnboardingFormData>(steps, {
  initialStep: () => {
    if (hasFullContext.value) {
      return "metricsNorthStar";
    }

    return steps.value[0]?.name ?? "context";
  },
  useLocalStorage: false,
  // Context fields are optional — allow jumping to Metrics from the stepper.
  freeMovement: true,
  initialData: {
    campaign: props.campaign,
    context: props.context,
  },
});
</script>

<template>
  <template v-if="createdFromBuilder">
    <FormStep name="brief">
      <LucaGuideCampaignOnboardingBrief />
    </FormStep>

    <FormStep name="creativeStrategyProposals">
      <LucaGuideCampaignOnboardingCreativeStrategy />
    </FormStep>

    <FormStep name="metricsNorthStar">
      <LucaGuideCampaignOnboardingMetrics />
    </FormStep>
  </template>

  <template v-else>
    <FormStep name="context">
      <LucaGuideCampaignOnboardingContext />
    </FormStep>

    <FormStep name="metricsNorthStar">
      <LucaGuideCampaignOnboardingMetrics />
    </FormStep>
  </template>
</template>
