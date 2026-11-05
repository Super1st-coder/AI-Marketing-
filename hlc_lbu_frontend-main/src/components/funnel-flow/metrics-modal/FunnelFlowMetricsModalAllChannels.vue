<script setup lang="ts">
import { CampaignChannelGroupData } from "@/services/projects/CampaignsApi";
import { MetricGroup } from "@/services/UtilsApi";

const isOpen = defineModel<boolean>({ required: true });

defineProps<{
  group: MetricGroup;
  metricsGroups: CampaignChannelGroupData[];
}>();
</script>

<template>
  <Modal v-model="isOpen" class="tw:p-10" :maxWidth="1100" closeButton>
    <div>
      <!-- Title -->
      <h2 class="tw:mb-7 tw:text-4xl tw:font-extrabold">
        {{
          $t(
            `funnel-flow.home.stages.metrics.view-${group.toLocaleLowerCase()}`,
          )
        }}
      </h2>

      <!-- Grid of cards -->
      <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:lg:grid-cols-3">
        <FunnelFlowMetricsModalMetricCard
          v-for="channel in metricsGroups"
          :key="channel.name"
          :channelName="channel.name"
          :group="group"
          :metrics="channel.metrics"
        >
          <template #title>
            {{ channel.name }}
          </template>
        </FunnelFlowMetricsModalMetricCard>
      </div>
    </div>
  </Modal>
</template>
