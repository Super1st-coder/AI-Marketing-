<script setup lang="ts">
import type { LucaGuideAdPerformanceSummaryKpi } from "@/services/guide/LucaGuideAdsApi";
import {
  getLucaGuideKpiChartColor,
  getLucaGuideKpiValueClass,
  type LucaGuideKpiTargetTone,
} from "@/utils/guide/kpi";

const props = defineProps<{
  kpi: LucaGuideAdPerformanceSummaryKpi;
  priorityLabel: string;
  kpiName: string;
  timeframeDays: number;
  hasData: boolean;
  currency?: string;
  highlighted?: boolean;
}>();

const { locale } = useI18n();

// HLG-176: pair the value and its good/bad styling from the SAME (windowed)
// source so a card never shows a windowed number with the lifetime good flag (or
// vice versa). With no data in the window both are null -> a neutral "—".
const isGood = computed(() => (props.hasData ? props.kpi.windowed_good : null));

const tone = computed<LucaGuideKpiTargetTone>(() =>
  isGood.value ? "success" : "error",
);

const chartColor = computed(() => getLucaGuideKpiChartColor(tone.value));
const valueClass = computed(() => getLucaGuideKpiValueClass(isGood.value));

const formattedValue = computed(() =>
  formatLucaGuideKpiValue(
    props.hasData ? props.kpi.windowed_value : null,
    props.kpi.format,
    locale.value,
    props.currency,
  ),
);

const formattedTarget = computed(() =>
  formatLucaGuideKpiValue(
    props.kpi.target,
    props.kpi.format,
    locale.value,
    props.currency,
  ),
);

const hasTrendData = computed(() => props.kpi.series.length > 0);

function formatChartValue(value: number) {
  return formatLucaGuideKpiValue(
    value,
    props.kpi.format,
    locale.value,
    props.currency,
  );
}
</script>

<template>
  <CardBase
    borderRadius="sm"
    class="tw:flex tw:flex-col tw:gap-1 tw:p-2.5"
    :shadow="false"
  >
    <div class="tw:flex tw:items-start tw:justify-between tw:gap-2 tw:text-sm">
      <p class="tw:text-gray-500">
        {{ priorityLabel }}
      </p>

      <p
        class="tw:text-right tw:font-bold"
        :class="{
          'tw:text-primary': highlighted,
          'tw:text-gray-600': !highlighted,
        }"
      >
        {{ kpiName }}
      </p>
    </div>

    <p class="tw:grow tw:leading-tight tw:font-bold">
      <span class="tw:text-xl" :class="valueClass">
        {{ formattedValue }}
      </span>

      <span class="tw:text-sm tw:font-normal tw:text-gray-400">
        / {{ formattedTarget }}
      </span>
    </p>

    <LucaGuideKpiSparkline
      v-if="hasTrendData"
      :data="kpi.series"
      :color="chartColor"
      :formatValue="formatChartValue"
    />

    <p
      v-else
      class="tw:flex tw:h-[60px] tw:items-center tw:justify-center tw:text-center tw:text-xs tw:text-gray-400"
    >
      {{
        $t("luca-guide.ads.detail.performance-summary.no-trend-data", {
          days: timeframeDays,
        })
      }}
    </p>
  </CardBase>
</template>
