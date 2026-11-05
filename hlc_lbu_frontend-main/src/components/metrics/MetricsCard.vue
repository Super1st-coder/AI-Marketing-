<script setup lang="ts">
import { MetricGroup } from "@/services/UtilsApi";
import { MetricsChannelGroup } from "./types";

const props = withDefaults(
  defineProps<{
    channelGroup: MetricsChannelGroup;
    metricGroupName: MetricGroup;
    showNoDataAvailable?: boolean;
    cardMinHeight?: number;
  }>(),
  { cardMinHeight: 220 },
);

const { t } = useI18n();

const metrics = computed(
  () => props.channelGroup.groups[props.metricGroupName],
);

const _currentMetricIndex = ref(0);
const currentMetricIndex = computed<number>({
  get: () => _currentMetricIndex.value,
  set: (value) => {
    const n = value;
    const m = metrics.value.length;
    _currentMetricIndex.value = ((n % m) + m) % m;
  },
});
const currentMetric = computed(() => {
  const item = metrics.value[currentMetricIndex.value];

  if (!item) return undefined;
  return item;
});

const currentMetricFormattedValue = computed<string>(() => {
  const originalValue = currentMetric.value?.value;
  const numberValue = castStringToNumber(originalValue);

  const isCurrency = currentMetric.value?.unit === "$";
  if (isCurrency) {
    return formatCurrencyValue(numberValue, DEFAULT_NUMBER_LOCALE, "USD", true);
  }

  return numberValue.toLocaleString(DEFAULT_NUMBER_LOCALE, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 20,
  });
});

// Display last metric when metrics change
watch(metrics, (metrics) => {
  currentMetricIndex.value = metrics.length - 1;
});
</script>

<template>
  <CardBase
    class="tw:relative tw:flex tw:flex-col tw:items-center tw:justify-center tw:gap-5 tw:px-[5px] tw:pt-2.5 tw:pb-6"
    :style="{ minHeight: `${cardMinHeight}px` }"
  >
    <template v-if="metrics.length > 0 && currentMetric">
      <div
        class="tw:absolute tw:top-0 tw:right-0 tw:m-2.5 tw:rounded tw:border tw:border-current tw:px-1.5 tw:py-0.5 tw:text-sm tw:text-[#808390]"
      >
        {{
          $t("global.current-of-total", {
            current: currentMetricIndex + 1,
            total: metrics.length,
          })
        }}
      </div>

      <div class="tw:flex tw:self-stretch">
        <button
          type="button"
          @click="currentMetricIndex--"
          v-show="metrics.length > 1"
        >
          <Icon
            icon="tabler-chevron-left"
            class="tw:text-xl tw:text-primary tw:sm:text-3xl tw:lg:text-xl"
          />
        </button>

        <div class="tw:flex tw:grow tw:flex-col tw:items-center">
          <h3 class="tw:text-center tw:font-bold">
            {{
              t(
                `campaigns.metric-groups.metrics.${currentMetric.name}.display_name`,
                currentMetric.display_name!,
              )
            }}
          </h3>

          <p class="tw:text-center">
            <span
              class="tw:flex tw:items-center tw:justify-center tw:gap-2 tw:lg:gap-4"
            >
              <span class="tw:text-xl tw:font-bold tw:lg:text-2xl">{{
                currentMetricFormattedValue
              }}</span>
              {{ " " }}
              <span v-if="currentMetric.unit" class=""
                >{{ currentMetric.unit }}
              </span>
            </span>
            {{ " " }}
            <span class="tw:text-sm tw:font-normal tw:text-secondary-text">{{
              t(
                `campaigns.metric-groups.metrics.${currentMetric.name}.target`,
                currentMetric.target!,
              )
            }}</span>
          </p>
        </div>

        <button
          type="button"
          @click="currentMetricIndex++"
          v-show="metrics.length > 1"
        >
          <Icon
            icon="tabler-chevron-right"
            class="tw:text-xl tw:text-primary tw:sm:text-3xl tw:lg:text-xl"
          />
        </button>
      </div>
    </template>
    <template v-else-if="showNoDataAvailable">
      <p class="tw:text-center tw:text-sm tw:text-secondary-text">
        {{ $t("global.no-data-available") }}
      </p>
    </template>
    <template v-else>
      <h3 class="tw:text-center tw:text-lg tw:font-extrabold">
        {{ $t(`channel-groups.${channelGroup.name}.title`) }} <br />
        {{ $t(`campaigns.metric-groups.${metricGroupName}.name`) }}
      </h3>
    </template>

    <slot name="action" />
  </CardBase>
</template>
