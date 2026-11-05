<script setup lang="ts">
import { CampaignChannelGroupMetric } from "@/services/projects/CampaignsApi";
import { MetricGroup } from "@/services/UtilsApi";

const props = defineProps<{
  channelName: string;
  group: MetricGroup;
  metrics?: CampaignChannelGroupMetric[] | null;
}>();

const metricIcon = (metricName: string) => {
  switch (metricName) {
    case "Paid Social":
      return "tabler-speakerphone";
    case "Paid Search":
      return "tabler-mouse";
    case "Organic Search":
      return "tabler-search";
    default:
      return "tabler-chart-bar";
  }
};

const metricColor = (metricName: string) => {
  switch (metricName) {
    case "Paid Social":
      return "success";
    case "Paid Search":
      return "primary";
    case "Organic Search":
      return "info";
    default:
      return "gray";
  }
};

const metrics = computed(() => {
  return props.metrics?.filter((metric) => metric.group === props.group) ?? [];
});
</script>

<template>
  <div
    class="tw:flex tw:flex-col tw:gap-3 tw:rounded-2xl tw:bg-secondary/10 tw:p-4"
  >
    <!-- Channel Header -->
    <div class="tw:flex tw:items-center tw:gap-3">
      <IconCard
        :icon="metricIcon(channelName)"
        :variant="metricColor(channelName)"
        size="sm"
      />
      <span class="tw:font-semibold">
        <slot name="title" />
      </span>
    </div>

    <!-- Metrics slider -->
    <FunnelFlowMetricsModalMetricCardSlider :metrics="metrics" />
  </div>
</template>
