<script setup lang="ts">
import { CampaignChannelGroupData } from "@/services/projects/CampaignsApi";
import { MetricGroup } from "@/services/UtilsApi";

defineProps<{
  group: MetricGroup;
  metricsGroup: CampaignChannelGroupData;
}>();

const isOpen = defineModel<boolean>({ required: true });
</script>

<template>
  <Modal v-model="isOpen" class="tw:p-5 tw:sm:p-10" :maxWidth="500" closeButton>
    <h2 class="tw:mb-7 tw:text-4xl tw:font-extrabold">
      {{ metricsGroup.name }}
      {{ group == "Marketing" ? "KPIs" : group }}
    </h2>

    <FunnelFlowMetricsModalMetricCard
      :channelName="metricsGroup.name"
      :group="group"
      :metrics="metricsGroup.metrics"
    >
      <template #title>
        {{ group == "Marketing" ? "KPIs" : group }}
      </template>
    </FunnelFlowMetricsModalMetricCard>
  </Modal>
</template>
