<script lang="ts" setup>
import { getGroupChannelStyles } from "@/constants/campaigns";
import { CampaignChannelGroupData } from "@/services/projects/CampaignsApi";
import { MetricGroup, metricGroups } from "@/services/UtilsApi";

const props = defineProps<{
  data: CampaignChannelGroupData;
}>();

const emit = defineEmits<{
  previewMetrics: [group: MetricGroup, metricsGroup: CampaignChannelGroupData];
}>();

const metadata = computed(() => getGroupChannelStyles(props.data.name));
</script>

<template>
  <div class="tw:flex tw:w-full">
    <CardBase
      class="tw:flex tw:grow tw:items-stretch tw:gap-3 tw:p-3 tw:md:p-5"
    >
      <!-- Main card content -->
      <div class="tw:flex tw:grow tw:flex-col tw:gap-5">
        <div
          class="tw:flex tw:flex-col tw:justify-between tw:gap-6 tw:lg:flex-row tw:lg:items-center"
        >
          <CardTitle :iconVariant="metadata.color" :icon="metadata.icon">
            {{ $t(`channel-groups.${props.data.name}.title`) }}

            <template #subtitle>
              {{ $t(`channel-groups.${props.data.name}.description`) }}
            </template>
          </CardTitle>

          <Button
            v-if="metadata.availableInFunnelFlow"
            leftIcon="tabler-plus"
            :to="metadata.route"
            size="md"
            class="tw:min-w-fit"
          >
            {{ $t("funnel-flow.paid-social.stage-card.setup") }}
          </Button>
          <Chip v-else size="md">{{ $t("global.soon") }}</Chip>
        </div>

        <Separator v-if="data.metrics?.length" />

        <div v-if="data.metrics?.length" class="tw:flex tw:flex-wrap tw:gap-4">
          <Button
            v-for="group in metricGroups"
            :key="group"
            color="secondary"
            size="sm"
            variant="outlined"
            @click="emit('previewMetrics', group, data)"
          >
            {{
              $t(
                `funnel-flow.home.stages.metrics.view-${group.toLocaleLowerCase()}`,
              )
            }}
          </Button>
        </div>
      </div>
    </CardBase>
  </div>
</template>
