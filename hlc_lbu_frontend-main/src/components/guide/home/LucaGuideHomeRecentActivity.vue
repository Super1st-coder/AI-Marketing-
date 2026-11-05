<script setup lang="ts">
import type { LucaGuideRecentActivityItem } from "@/services/guide/LucaGuideDashboardApi";
import { formatCompactRelativeTime } from "@/utils/dates";

const props = defineProps<{
  activities: LucaGuideRecentActivityItem[];
}>();

const ACTIVITY_ICONS: Record<string, string> = {
  chart: "tabler:chart-bar",
  bolt: "tabler:bolt",
  inbox: "tabler:inbox",
  flask: "tabler:flask",
  beaker: "tabler:test-pipe",
  layers: "tabler:stack-2",
};

function getActivityIcon(icon: string) {
  return ACTIVITY_ICONS[icon] ?? "tabler:history";
}
</script>

<template>
  <CardBase class="tw:flex tw:h-full tw:flex-col tw:p-4" style="height: 400px">
    <div class="tw:mb-4">
      <h2
        class="tw:mb-1 tw:flex tw:items-center tw:gap-2 tw:text-xl tw:font-bold"
      >
        <Icon icon="tabler:history" class="tw:text-[24px]" />

        <span>{{ $t("luca-guide.home.activity.title") }}</span>
      </h2>

      <p class="tw:text-sm tw:text-secondary-text">
        {{ $t("luca-guide.home.activity.description") }}
      </p>
    </div>

    <div
      v-if="props.activities.length"
      class="tw:divide-y tw:divide-gray-200 tw:overflow-y-auto tw:pr-2"
    >
      <LucaGuideHomeRecentActivityItem
        v-for="(activity, index) in props.activities"
        :key="`${activity.at}-${index}`"
        :icon="getActivityIcon(activity.icon)"
        :title="activity.title"
        :description="activity.subtitle"
        :time="formatCompactRelativeTime(activity.at)"
      />
    </div>

    <p v-else class="tw:text-sm tw:text-secondary-text">
      {{ $t("luca-guide.home.activity.empty") }}
    </p>
  </CardBase>
</template>
