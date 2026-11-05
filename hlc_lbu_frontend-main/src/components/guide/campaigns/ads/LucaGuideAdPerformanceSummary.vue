<script setup lang="ts">
import LucaGuideAdsApi, {
  type LucaGuideAdPerformanceSummary,
} from "@/services/guide/LucaGuideAdsApi";
import type { LucaGuideTimeframe } from "@/components/guide/LucaGuideTimeFilters.vue";

const props = defineProps<{
  adExternalId: string;
  currency?: string;
}>();

const emit = defineEmits<{
  // Lift the resolved window up so the Ad Diagnosis can be regenerated for the SAME dates (Marco).
  "window-change": [{ startDate?: string; endDate?: string }];
  // HLG-158: the page badge must reflect the SAME windowed classification as the
  // summary text (the badge was showing the lifetime state while the text was
  // windowed). Publish the current window's state so the ad page can bind its badge.
  "update:windowedState": [
    state: LucaGuideAdPerformanceSummary["windowed_state"] | null,
  ];
}>();

const { t, te, locale } = useI18n();

const isRefreshing = ref(false);
const summary = ref<LucaGuideAdPerformanceSummary>(
  await LucaGuideAdsApi.getPerformanceSummary(props.adExternalId, {
    days: 7,
    autoRange: true,
  }),
);
const timeframe = ref<LucaGuideTimeframe>({
  type: "custom-range",
  startDate: summary.value.window_start,
  endDate: summary.value.window_end,
});

watch(
  summary,
  () =>
    emit("window-change", {
      startDate: summary.value.window_start ?? undefined,
      endDate: summary.value.window_end ?? undefined,
    }),
  { immediate: true },
);

const primaryKpi = computed(() =>
  summary.value.kpis.find((kpi) => kpi.priority === "primary"),
);

watch(
  () => [summary.value.windowed_state, summary.value.has_data] as const,
  ([state, hasData]) =>
    emit("update:windowedState", hasData ? (state ?? null) : null),
  { immediate: true },
);

const summaryText = computed(() => {
  // HLG-176: the justification must be built from the SELECTED window, not the
  // stored lifetime `explanation` (which would sit above the windowed KPI cards
  // and mix the two). Always derive it from the windowed state + windowed value.
  if (!summary.value.has_data) {
    return t("luca-guide.ads.detail.performance-summary.no-data-for-period");
  }

  const primary = primaryKpi.value;
  if (!primary) {
    return null;
  }

  const windowedState = summary.value.windowed_state;
  const statusKey = `luca-guide.onboarding.classification-thresholds.statuses.${windowedState}`;
  const stateLabel = te(statusKey) ? t(statusKey) : windowedState;
  const kpiName = kpiNameFor(primary.key, primary.name);
  const value = formatLucaGuideKpiValue(
    primary.windowed_value,
    primary.format,
    locale.value,
    props.currency,
  );
  const target = formatLucaGuideKpiValue(
    primary.target,
    primary.format,
    locale.value,
    props.currency,
  );

  // HLG-176: the "meeting/missing" verb must reflect the actual windowed value vs target
  // (windowed_good), NOT the state tier. A Promising ad can still BEAT its target (good cost, just
  // not enough volume for Scalable/Winner) — driving the verb off the state wrongly read
  // "Promising … is missing" for a value under target. The backend now derives the state from the
  // same windowed value, so state and windowed_good agree (a Winner is always meeting, a Losing
  // always missing); using windowed_good fixes the Promising/gap cases without reintroducing
  // "Winner … missing".
  const isMeetingTarget = Boolean(primary.windowed_good);

  return t(
    isMeetingTarget
      ? "luca-guide.ads.detail.performance-summary.meeting-target"
      : "luca-guide.ads.detail.performance-summary.missing-target",
    { state: stateLabel, kpi: kpiName, value, target },
  );
});

// HLG-156: label the exact dates the window covers, so QA can compare like-for-like
// with Ads Manager instead of guessing whether it is a rolling or fixed range.
const windowRangeLabel = computed(() =>
  summary.value.window_start && summary.value.window_end
    ? formatDateRange(
        parseLocalIsoDate(summary.value.window_start),
        parseLocalIsoDate(summary.value.window_end),
        locale.value,
      )
    : null,
);

function kpiNameFor(key: string, fallback: string) {
  const translationKey = `luca-guide.kpis.${key}.short`;
  return te(translationKey) ? t(translationKey) : fallback;
}

async function loadSummary(next: LucaGuideTimeframe) {
  isRefreshing.value = true;

  try {
    const query =
      next.type === "custom-range"
        ? { startDate: next.startDate, endDate: next.endDate }
        : { days: next.type === "days" ? next.days : 7 };

    summary.value = await LucaGuideAdsApi.getPerformanceSummary(
      props.adExternalId,
      query,
    );
    await sleep(500);
  } catch (error) {
    console.error("Failed to load performance summary:", error);
    throw error;
  } finally {
    isRefreshing.value = false;
  }
}
</script>

<template>
  <AccordionList v-if="summary" variant="card">
    <Accordion
      openByDefault
      shrinkActions
      titleClass="tw:text-lg tw:font-bold tw:whitespace-nowrap"
    >
      <template #title>
        {{ $t("luca-guide.ads.detail.performance-summary.title") }}
      </template>

      <template #actions>
        <LucaGuideTimeFilters
          v-model="timeframe"
          :options="[7, 14, 30, 'custom-range']"
          :disabled="isRefreshing"
          class="tw:justify-end"
          @update:model-value="loadSummary"
        />
      </template>

      <div
        class="tw:flex tw:flex-col tw:gap-4"
        :class="{ 'tw:pointer-events-none tw:opacity-50': isRefreshing }"
      >
        <p v-if="summaryText" class="tw:text-sm tw:text-secondary-text">
          {{ summaryText }}
        </p>

        <p class="tw:text-sm tw:text-secondary-text tw:uppercase">
          {{
            $t("luca-guide.ads.detail.performance-summary.trend-label", {
              days: summary.window_days,
            })
          }}
          <span v-if="windowRangeLabel" class="tw:normal-case">
            · {{ windowRangeLabel }}
          </span>
        </p>

        <div class="tw:grid tw:grid-cols-1 tw:gap-4 tw:lg:grid-cols-3">
          <LucaGuideAdPerformanceSummaryKpiCard
            v-for="kpi in summary.kpis"
            :key="kpi.priority"
            :kpi="kpi"
            :priorityLabel="
              $t(`luca-guide.north-star-kpi-priorities.${kpi.priority}-kpi`)
            "
            :kpiName="kpiNameFor(kpi.key, kpi.name)"
            :timeframeDays="summary.window_days"
            :hasData="summary.has_data"
            :currency="currency"
            :highlighted="kpi.priority === 'primary'"
          />
        </div>
      </div>
    </Accordion>
  </AccordionList>
</template>
