<script setup lang="ts">
import { CampaignChannelGroupMetric } from "@/services/projects/CampaignsApi";

const props = defineProps<{
  metrics?: CampaignChannelGroupMetric[] | null;
}>();

const _currentMetricIndex = ref(0);
const currentMetricIndex = computed<number>({
  get: () => _currentMetricIndex.value,
  set: (value) => {
    const n = value;
    const m = props.metrics?.length ?? 0;
    _currentMetricIndex.value = ((n % m) + m) % m;
  },
});

const currentMetric = computed(() => {
  const item = props.metrics?.[currentMetricIndex.value];

  if (!item) return undefined;
  return item;
});

watch(
  () => props.metrics,
  () => {
    currentMetricIndex.value = 0;
  },
);

const currentMetricFormattedValue = (
  value: string | number | undefined | null,
  unit?: string | null,
) => {
  const numberValue = castStringToNumber(value);

  const isCurrency = unit === "$";
  if (isCurrency) {
    return formatCurrencyValue(numberValue, DEFAULT_NUMBER_LOCALE, "USD", true);
  }

  return numberValue.toLocaleString(DEFAULT_NUMBER_LOCALE, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 20,
  });
};
</script>

<template>
  <CardBase
    class="tw:relative tw:flex tw:min-h-[220px] tw:w-full tw:flex-col tw:items-center tw:justify-center tw:gap-5 tw:px-[5px] tw:pt-2.5 tw:pb-4"
  >
    <template v-if="props.metrics && props.metrics.length > 0 && currentMetric">
      <div
        class="tw:absolute tw:top-0 tw:right-0 tw:m-2.5 tw:rounded tw:border tw:border-secondary tw:px-1.5 tw:py-0.5 tw:text-sm"
      >
        {{
          $t("global.current-of-total", {
            current: currentMetricIndex + 1,
            total: props.metrics.length,
          })
        }}
      </div>

      <div class="tw:flex tw:self-stretch">
        <button
          type="button"
          @click="currentMetricIndex--"
          v-show="props.metrics.length > 1"
        >
          <Icon
            icon="tabler-chevron-left"
            class="tw:text-xl tw:text-primary tw:sm:text-3xl tw:lg:text-xl"
          />
        </button>

        <div
          :key="currentMetric.name"
          class="tw:flex tw:grow tw:flex-col tw:items-center"
        >
          <h3 class="tw:text-center tw:text-lg tw:font-extrabold">
            {{ currentMetric.display_name }}
          </h3>

          <div class="tw:text-center">
            <div
              class="tw:flex-wrap tw:justify-center tw:gap-2 tw:text-xl tw:font-extrabold tw:lg:flex tw:lg:gap-4 tw:lg:text-[28px]"
            >
              <span>{{
                currentMetricFormattedValue(
                  currentMetric.value,
                  currentMetric.unit,
                )
              }}</span>
              <span v-if="currentMetric.unit">{{ currentMetric.unit }} </span>
            </div>
            <div class="tw:font-normal">{{ currentMetric.target }}</div>
          </div>
        </div>

        <button
          type="button"
          @click="currentMetricIndex++"
          v-show="props.metrics.length > 1"
        >
          <Icon
            icon="tabler-chevron-right"
            class="tw:text-xl tw:text-primary tw:sm:text-3xl tw:lg:text-xl"
          />
        </button>
      </div>
    </template>
    <template v-else>
      {{ $t("global.no-data-available") }}
    </template>
  </CardBase>
</template>
