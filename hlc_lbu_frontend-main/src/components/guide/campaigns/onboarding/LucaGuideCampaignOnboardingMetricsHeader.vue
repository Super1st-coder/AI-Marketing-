<script setup lang="ts">
import type { LucaGuideCampaign } from "@/services/guide/LucaGuideCampaignsApi";

const props = defineProps<{
  campaign: LucaGuideCampaign;
}>();

const { t, te, tm } = useI18n();

function getCampaignObjective() {
  const key = props.campaign.objective;
  if (!key) return "-";

  if (te(`meta-ads.objectives.${key}.title`)) {
    return t(`meta-ads.objectives.${key}.title`);
  }

  return props.campaign.objective_label || key;
}

function getOptimizationGoal() {
  const key = props.campaign.optimization_goal;
  if (!key) return "-";

  // Campaigns imported from Meta can pair an objective with a goal that is
  // only translated under another objective, so the campaign's objective is
  // tried first and then any objective that has a label for the goal
  const objectives = [
    props.campaign.objective,
    ...Object.keys(tm("meta-ads.objectives")),
  ];

  for (const objective of objectives) {
    const i18nKey = `meta-ads.objectives.${objective}.optimization-goals.${key}.title`;
    if (te(i18nKey)) {
      return t(i18nKey);
    }
  }

  return key;
}

const stats = computed(() => [
  {
    labelKey:
      "luca-guide.campaigns.onboarding.metrics-north-star.campaign-objective",
    value: getCampaignObjective(),
  },
  {
    labelKey:
      "luca-guide.campaigns.onboarding.metrics-north-star.optimization-goal",
    value: getOptimizationGoal(),
  },
  {
    labelKey:
      "luca-guide.campaigns.onboarding.metrics-north-star.campaign-mode",
    value: "-",
  },
  {
    labelKey:
      "luca-guide.campaigns.onboarding.metrics-north-star.budget-optimization",
    value: "-",
  },
]);
</script>

<template>
  <CardBase borderRadius="md" class="tw:grid tw:grid-cols-1 tw:gap-5 tw:p-6">
    <div class="tw:flex tw:items-start tw:gap-3">
      <IconCard icon="tabler:speakerphone" variant="success" size="lg" />

      <div class="tw:grid tw:min-w-0 tw:grow tw:grid-cols-1 tw:gap-2">
        <h2 class="tw:text-xl tw:font-bold">
          {{ campaign.name }}
        </h2>

        <div class="tw:flex tw:flex-wrap tw:gap-6 tw:gap-y-2 tw:text-sm">
          <div v-for="stat in stats" :key="stat.labelKey">
            <span class="tw:text-secondary"> {{ $t(stat.labelKey) }} : </span>
            <span class="tw:ml-1 tw:font-semibold">{{ stat.value }}</span>
          </div>
        </div>
      </div>
    </div>
  </CardBase>
</template>
