<script setup lang="ts">
import LucaGuideCampaignsApi, {
  type LucaGuideCampaignBrief,
  type LucaGuideCampaignBriefMetric,
} from "@/services/guide/LucaGuideCampaignsApi";
import type {
  MetricsChannelGroup,
  MetricsItem,
} from "@/components/metrics/types";

// HLG-120: the channel-group brief (Goals / Resources / Performance KPIs) resolved from the
// campaign's LINKED Builder campaign. Meta-imported campaigns with no linked context — or Builder
// unreachable — return has_brief:false and we keep the "Nothing in the brief" placeholder.
const route = useRoute();
const campaignId = String(route.params.campaignId);

const brief = ref<LucaGuideCampaignBrief>({
  has_brief: false,
  channel_groups: [],
});
const loading = ref(true);

onMounted(async () => {
  try {
    brief.value = await LucaGuideCampaignsApi.getBrief(campaignId);
  } finally {
    loading.value = false;
  }
});

const toMetricsItem = (metric: LucaGuideCampaignBriefMetric): MetricsItem => ({
  name: metric.label,
  display_name: metric.label,
  value: metric.value,
  unit: metric.unit,
  target: metric.target,
});

const channelGroups = computed((): MetricsChannelGroup[] =>
  brief.value.channel_groups.map((group) => ({
    name: group.name ?? "",
    groups: {
      Goals: group.goals.map(toMetricsItem),
      Resources: group.resources.map(toMetricsItem),
      Marketing: group.performance_kpis.map(toMetricsItem),
    },
  })),
);
</script>

<template>
  <CardBase
    v-if="loading"
    borderRadius="md"
    class="tw:flex tw:items-center tw:gap-3 tw:p-6"
  >
    <IconCard icon="tabler:speakerphone" variant="success" size="lg" />
    <p class="tw:text-secondary-text">
      {{
        $t("luca-guide.campaigns.onboarding.metrics-north-star.brief-loading")
      }}
    </p>
  </CardBase>

  <!-- Meta-imported / no linked Builder brief -->
  <CardBase
    v-else-if="!brief.has_brief"
    borderRadius="md"
    class="tw:flex tw:items-center tw:gap-3 tw:p-6"
  >
    <IconCard icon="tabler:speakerphone" variant="success" size="lg" />
    <p class="tw:text-secondary-text">
      {{ $t("luca-guide.campaigns.onboarding.metrics-north-star.empty-brief") }}
    </p>
  </CardBase>

  <!-- Builder brief: Goals / Resources / Performance KPIs per channel group -->
  <CardBase v-else class="tw:p-6">
    <MetricsMatrix
      :channelGroups="channelGroups"
      showNoDataAvailable
      :cardMinHeight="180"
    />
  </CardBase>
</template>
