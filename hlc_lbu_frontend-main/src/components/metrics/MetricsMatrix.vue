<script setup lang="ts">
import { metricGroups, type MetricGroup } from "@/services/UtilsApi";
import {
  groupChannelStyles,
  metricGroupColumnStyles,
} from "@/constants/campaigns";
import type { MetricsChannelGroup } from "./types";

defineProps<{
  channelGroups: MetricsChannelGroup[];
  showNoDataAvailable?: boolean;
  cardMinHeight?: number;
}>();

defineSlots<{
  action(props: { index: number; metricGroupName: MetricGroup }): void;
}>();
</script>

<template>
  <div class="tw:grid tw:gap-6 tw:lg:grid-cols-4">
    <div class="tw:hidden tw:lg:block"></div>
    <div
      v-for="metricGroupName in metricGroups"
      :key="metricGroupName"
      class="tw:hidden tw:lg:block"
    >
      <div class="tw:flex tw:items-center tw:gap-4">
        <IconCard
          :icon="metricGroupColumnStyles[metricGroupName]?.icon"
          :variant="metricGroupColumnStyles[metricGroupName]?.variant"
          size="md"
        />

        <h2 class="tw:font-bold">
          {{ $t(`campaigns.metric-groups.${metricGroupName}.name`) }}
        </h2>
      </div>
    </div>

    <template v-for="(group, index) in channelGroups">
      <div
        class="tw:flex tw:items-center tw:gap-3 tw:p-4 tw:lg:flex-col tw:lg:items-start tw:lg:justify-center"
      >
        <IconCard
          :icon="groupChannelStyles[group.name]?.icon"
          :variant="groupChannelStyles[group.name]?.color"
          size="lg"
        />

        <h2 class="tw:text-lg tw:font-bold">
          {{ $t(`channel-groups.${group.name}.title`) }}
        </h2>
      </div>

      <MetricsCard
        v-for="metricGroupName in metricGroups"
        :channelGroup="group"
        :metricGroupName="metricGroupName"
        :showNoDataAvailable="showNoDataAvailable"
        :cardMinHeight="cardMinHeight"
      >
        <template #action>
          <slot
            name="action"
            :index="index"
            :metricGroupName="metricGroupName"
          />
        </template>
      </MetricsCard>
    </template>
  </div>
</template>
