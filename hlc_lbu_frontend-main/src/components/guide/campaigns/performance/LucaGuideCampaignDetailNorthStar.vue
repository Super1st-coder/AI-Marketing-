<script setup lang="ts">
import type { LucaGuideCampaignKpisResponse } from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideKpi } from "@/services/guide/LucaGuideKpisApi";
import { LUCA_GUIDE_NORTH_STAR_PRIORITIES } from "@/services/guide/LucaGuideOnboardingApi";

const props = defineProps<{
  kpis: LucaGuideCampaignKpisResponse;
  kpiOptions: LucaGuideKpi[];
  // HLG-193: windowed header totals (loaded daily span) so the header matches the ad-set
  // list + ads table below it, instead of the stored all-time campaign aggregate.
  spend: number;
  impressions: number;
  conversions: number;
  adCount: number;
  currency?: string;
}>();

const emit = defineEmits<{
  editMetrics: [];
}>();

const { t, te, locale } = useI18n();

const kpiById = computed(() => {
  const map = new Map<string, LucaGuideKpi>();
  for (const option of props.kpiOptions) {
    map.set(option.id, option);
  }
  return map;
});

const primaryKpi = computed(() =>
  props.kpis.items.find((item) => item.priority === "primary"),
);

const primaryKpiMeta = computed(() => {
  const id = primaryKpi.value?.kpi_id;
  return id ? kpiById.value.get(id) : undefined;
});

const primaryKpiName = computed(() => {
  const meta = primaryKpiMeta.value;
  if (!meta) {
    return "—";
  }

  const key = `luca-guide.kpis.${meta.key}.short`;
  return te(key) ? t(key) : meta.name;
});

const showMisalignmentAlert = computed(
  () => props.kpis.has_misaligned && primaryKpi.value?.aligned === false,
);

const misalignmentWarning = computed(() => {
  const warning = primaryKpiMeta.value?.warning?.trim();
  if (warning) {
    return warning;
  }

  return t("luca-guide.campaigns.detail.misalignment.description");
});

type KpiCardModel = {
  priority: string;
  priorityLabel: string;
  kpiName: string;
  value: string;
  targetLabel: string;
  deltaLabel?: string;
  deltaOverTarget?: boolean;
  tone: "success" | "warning" | "error" | "secondary";
  highlighted: boolean;
  reasonLabel?: string;
};

const kpiCards = computed((): KpiCardModel[] => {
  return LUCA_GUIDE_NORTH_STAR_PRIORITIES.flatMap(
    (priority): KpiCardModel[] => {
      const item = props.kpis.items.find(
        (entry) => entry.priority === priority,
      );
      if (!item) {
        return [];
      }

      const meta = kpiById.value.get(item.kpi_id);
      const format = meta?.format_type;
      const lowerIsBetter = meta?.direction === "lower_is_better";
      const shortKey = meta ? `luca-guide.kpis.${meta.key}.short` : "";
      const kpiName = meta ? (te(shortKey) ? t(shortKey) : meta.name) : "—";

      const current =
        item.current_value == null ? null : Number(item.current_value);
      const target = Number(item.target_value);
      const hasCurrent =
        current != null && !Number.isNaN(current) && item.has_data;

      const value = formatCompactLucaGuideKpiValue(
        hasCurrent ? current : null,
        format,
        locale.value,
        props.currency,
      );

      const targetFormatted = formatCompactLucaGuideKpiValue(
        Number.isNaN(target) ? null : target,
        format,
        locale.value,
        props.currency,
      );

      // When the value is blank, explain WHY (Meta doesn't report it for this objective, or not
      // enough data yet) instead of a bare "—".
      const reasonKey = item.unavailable_reason
        ? `luca-guide.campaigns.detail.kpi.unavailable.${item.unavailable_reason}`
        : "";
      const reasonLabel =
        !hasCurrent && reasonKey && te(reasonKey)
          ? t(reasonKey, { kpi: kpiName })
          : undefined;

      let tone: KpiCardModel["tone"] = "secondary";
      let deltaLabel: string | undefined;
      let deltaOverTarget: boolean | undefined;

      if (hasCurrent && !Number.isNaN(target) && target !== 0) {
        const isOver = current > target;
        const pct = Math.abs(((current - target) / target) * 100);
        const pctLabel =
          pct >= 10 || Number.isInteger(pct)
            ? String(Math.round(pct))
            : pct.toFixed(2).replace(/\.?0+$/, "");

        tone = getLucaGuideKpiTargetTone(
          current,
          target,
          lowerIsBetter,
          hasCurrent,
        );
        deltaOverTarget = isOver;

        deltaLabel = t(
          isOver
            ? "luca-guide.campaigns.detail.kpi.over-target"
            : "luca-guide.campaigns.detail.kpi.under-target",
          { percent: pctLabel },
        );
      }

      return [
        {
          priority,
          priorityLabel: t(
            `luca-guide.north-star-kpi-priorities.${priority}-kpi`,
          ),
          kpiName,
          value,
          targetLabel: t("luca-guide.campaigns.detail.kpi.target", {
            value: targetFormatted,
          }),
          deltaLabel,
          deltaOverTarget,
          tone,
          highlighted: priority === "primary",
          reasonLabel,
        },
      ];
    },
  );
});

const footerStats = computed(() => [
  {
    label: t("luca-guide.campaigns.detail.stats.total-spend"),
    value: formatCompactCurrency(props.spend, locale.value, props.currency),
  },
  {
    label: t("luca-guide.campaigns.detail.stats.impressions"),
    value: formatCompactCount(props.impressions, locale.value),
  },
  {
    label: t("luca-guide.campaigns.detail.stats.conversions"),
    value:
      props.conversions > 0
        ? formatCompactCount(props.conversions, locale.value)
        : t("luca-guide.campaigns.detail.stats.not-available"),
  },
  {
    label: t("luca-guide.campaigns.detail.stats.total-ads"),
    value: formatCompactCount(props.adCount, locale.value),
  },
]);
</script>

<template>
  <div class="tw:flex tw:flex-col tw:gap-10">
    <Alert v-if="showMisalignmentAlert" type="error" expandable>
      <template #title>
        {{ $t("luca-guide.campaigns.detail.misalignment.title") }}
      </template>

      <template #custom>
        <p class="tw:mb-3 tw:font-normal">
          {{ misalignmentWarning }}
        </p>

        <div class="tw:flex tw:flex-wrap tw:items-center tw:gap-3">
          <Button
            type="button"
            color="error"
            size="sm"
            leftIcon="tabler:pencil"
            :shadow="false"
            @click="emit('editMetrics')"
          >
            {{ $t("luca-guide.campaigns.detail.misalignment.adjust") }}
          </Button>
        </div>
      </template>
    </Alert>

    <CardBase borderRadius="md" class="tw:flex tw:flex-col tw:gap-5 tw:p-6">
      <div
        class="tw:flex tw:flex-col tw:gap-3 tw:sm:flex-row tw:sm:items-center tw:sm:justify-between"
      >
        <h2
          class="tw:flex tw:items-center tw:gap-2 tw:text-lg tw:font-bold tw:text-secondary"
        >
          <Icon
            icon="custom:north-star"
            class="tw:text-[24px] tw:text-primary"
          />

          <span>
            {{
              $t("luca-guide.campaigns.detail.north-star-title", {
                kpi: primaryKpiName,
              })
            }}
          </span>
        </h2>

        <Button
          type="button"
          variant="outlined"
          color="secondary"
          size="sm"
          leftIcon="tabler:pencil"
          :shadow="false"
          @click="emit('editMetrics')"
        >
          {{ $t("luca-guide.campaigns.detail.edit-metrics") }}
        </Button>
      </div>

      <div class="tw:grid tw:grid-cols-1 tw:gap-5 tw:lg:grid-cols-3">
        <LucaGuideCampaignDetailKpiCard
          v-for="card in kpiCards"
          :key="card.priority"
          :priorityLabel="card.priorityLabel"
          :kpiName="card.kpiName"
          :value="card.value"
          :targetLabel="card.targetLabel"
          :deltaLabel="card.deltaLabel"
          :deltaOverTarget="card.deltaOverTarget"
          :tone="card.tone"
          :highlighted="card.highlighted"
          :reasonLabel="card.reasonLabel"
        />
      </div>

      <Separator />

      <div class="tw:grid tw:grid-cols-2 tw:gap-4 tw:lg:grid-cols-4">
        <div
          v-for="stat in footerStats"
          :key="stat.label"
          class="tw:flex tw:flex-col tw:gap-1 tw:md:items-center"
        >
          <p class="tw:text-sm tw:text-secondary-text">
            {{ stat.label }}
          </p>

          <p class="tw:text-lg tw:font-bold">
            {{ stat.value }}
          </p>
        </div>
      </div>
    </CardBase>
  </div>
</template>
