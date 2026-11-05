<script setup lang="ts">
import type { LucaGuideCampaignsOverview } from "@/services/guide/LucaGuideCampaignsApi";
import { LUCA_GUIDE_NORTH_STAR_PRIORITIES } from "@/services/guide/LucaGuideOnboardingApi";

const props = defineProps<{
  overview: LucaGuideCampaignsOverview;
  periodDays?: number;
}>();

const { t, te, locale } = useI18n();

const showNorthStarAlert = ref(false);

const currency = computed(() => props.overview.currency);

type NorthStarMetricCard = {
  label: string;
  value: string;
  target?: string;
  secondary?: string;
};

const northStarMetrics = computed((): NorthStarMetricCard[] => {
  const priorityCards = LUCA_GUIDE_NORTH_STAR_PRIORITIES.flatMap(
    (priority): NorthStarMetricCard[] => {
      const item = props.overview.account_north_star.find(
        (entry) => entry.priority === priority,
      );
      if (!item) {
        return [];
      }

      const kpiLabelKey = `luca-guide.kpis.${item.key}.short`;

      const label = t(`luca-guide.campaigns.north-star.${priority}`, {
        kpi: te(kpiLabelKey) ? t(kpiLabelKey) : item.name,
      });

      const value = formatCompactLucaGuideKpiValue(
        item.value,
        item.format,
        locale.value,
        currency.value,
      );

      const target = formatCompactLucaGuideKpiValue(
        item.target,
        item.format,
        locale.value,
        currency.value,
      );

      return [
        {
          label,
          value,
          target,
        },
      ];
    },
  );

  return [
    ...priorityCards,
    {
      label: t("luca-guide.campaigns.north-star.spend"),
      value: formatCompactCurrency(
        props.overview.totals.spend,
        locale.value,
        currency.value,
      ),
      secondary: t("luca-guide.campaigns.north-star.conversions", {
        count: Math.round(props.overview.totals.conversions),
      }),
    },
    {
      label: t("luca-guide.campaigns.north-star.active-ads"),
      value: String(props.overview.totals.active_ads),
      // HLG-177: the account North Star is scoped to CONFIGURED campaigns. When some are still
      // pending setup, label it "N of M campaigns" so it doesn't look like it covers the whole
      // account; otherwise keep the plain count.
      secondary:
        props.overview.totals.total_campaigns >
        props.overview.totals.active_campaigns
          ? t("luca-guide.campaigns.north-star.campaigns-count-scoped", {
              active: props.overview.totals.active_campaigns,
              total: props.overview.totals.total_campaigns,
            })
          : t("luca-guide.campaigns.north-star.campaigns-count", {
              count: props.overview.totals.active_campaigns,
            }),
    },
  ];
});

const spendStatuses = computed(() =>
  CLASSIFICATION_THRESHOLDS.map((config) => {
    const bucket = props.overview.spend_distribution[config.key];

    return {
      key: config.key,
      icon: config.icon,
      color: config.color,
      label: t(
        `luca-guide.onboarding.classification-thresholds.statuses.${config.key}`,
      ),
      percent: `${Math.round(bucket.pct_spend)}%`,
      spend: formatCompactCurrency(bucket.spend, locale.value, currency.value),
      adsCount: bucket.ads,
    };
  }),
);
</script>

<template>
  <LucaGuideCampaignsMetricsSection>
    <template #title>
      {{ $t("luca-guide.campaigns.north-star.title") }}
    </template>

    <template #titleAfter>
      <Link
        is="button"
        color="info"
        leftIcon="tabler:info-circle"
        class="tw:text-sm tw:font-medium"
        @click="showNorthStarAlert = !showNorthStarAlert"
      >
        {{ $t("luca-guide.campaigns.north-star.whats-this") }}
      </Link>
    </template>

    <template v-if="showNorthStarAlert" #alert>
      <Alert type="info">
        {{ $t("luca-guide.campaigns.north-star.alert") }}
      </Alert>
    </template>

    <div class="tw:grid tw:grid-cols-2 tw:gap-3 tw:lg:grid-cols-5">
      <LucaGuideCampaignsMetricCard
        v-for="(metric, index) in northStarMetrics"
        :key="index"
        :label="metric.label"
        :value="metric.value"
        :target="metric.target"
        :secondary="metric.secondary"
      />
    </div>
  </LucaGuideCampaignsMetricsSection>

  <LucaGuideCampaignsMetricsSection>
    <template #title>
      {{ $t("luca-guide.campaigns.spend.title") }}
      <span class="tw:font-normal tw:tracking-normal tw:normal-case">
        ·
        {{
          periodDays != null
            ? $t("luca-guide.campaigns.spend.period", { days: periodDays })
            : $t("luca-guide.campaigns.spend.period-all")
        }}
      </span>
    </template>

    <CardBase
      borderRadius="lg"
      class="tw:grid tw:grid-cols-1 tw:divide-x tw:divide-y tw:divide-gray-200 tw:sm:grid-cols-2 tw:lg:grid-cols-4"
    >
      <LucaGuideCampaignsSpendStatusCard
        v-for="status in spendStatuses"
        :key="status.key"
        :icon="status.icon"
        :label="status.label"
        :color="status.color"
        :percent="status.percent"
        :spend="status.spend"
        :adsCount="status.adsCount"
      />
    </CardBase>
  </LucaGuideCampaignsMetricsSection>
</template>
