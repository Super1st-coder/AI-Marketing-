<script setup lang="ts">
import type {
  LucaGuideCampaignAdsTableAd,
  LucaGuideCampaignAdsTableKpi,
} from "@/services/guide/LucaGuideCampaignsApi";
import type { LucaGuideAdTrend } from "@/services/guide/LucaGuideAdsApi";

const props = defineProps<{
  campaignId: string;
  ads: LucaGuideCampaignAdsTableAd[];
  kpis: LucaGuideCampaignAdsTableKpi[];
  currency?: string;
  loading?: boolean;
}>();

const route = useRoute();
const router = useRouter();
const { t, te, locale } = useI18n();

const sortBy = ref<{ key: string; order: "asc" | "desc" }[]>([]);

const tableCellProps = { class: "tw:text-xs" };
const headerNowrapProps = { class: "tw:whitespace-nowrap tw:text-xs" };
const kpiHeaderProps = {
  class: "tw:whitespace-pre tw:text-[11px]",
};

function formatKpiColumnTitle(kpi: LucaGuideCampaignAdsTableKpi) {
  const priorityLabel = t(
    `luca-guide.north-star-kpi-priorities.${kpi.priority}-kpi`,
  );
  const targetLabel = t("luca-guide.campaigns.detail.ads-table.target", {
    value: formatLucaGuideKpiValue(
      kpi.target,
      kpi.format,
      locale.value,
      props.currency,
    ),
  });

  return `${priorityLabel}\n${kpi.name} · ${targetLabel}`;
}

const tableHeaders = computed(() => {
  const kpiHeaders = props.kpis.map((kpi, index) => ({
    title: formatKpiColumnTitle(kpi),
    key: `kpi_${index}`,
    sortable: true,
    headerProps: kpiHeaderProps,
    cellProps: tableCellProps,
    sortRaw: (a: LucaGuideCampaignAdsTableAd, b: LucaGuideCampaignAdsTableAd) =>
      compareNullableNumbers(
        a.values[index]?.value,
        b.values[index]?.value,
        sortBy.value.some(
          (item) => item.key === `kpi_${index}` && item.order === "desc",
        ),
      ),
  }));

  return [
    {
      title: t("luca-guide.campaigns.detail.ads-table.columns.status"),
      key: "state",
      sortable: true,
      headerProps: headerNowrapProps,
      cellProps: tableCellProps,
    },
    {
      title: t("luca-guide.campaigns.detail.ads-table.columns.ad-name"),
      key: "ad_name",
      sortable: true,
      headerProps: headerNowrapProps,
      cellProps: tableCellProps,
    },
    ...kpiHeaders,
    {
      title: t("luca-guide.campaigns.detail.ads-table.columns.spend"),
      key: "spend",
      sortable: true,
      align: "end" as const,
      headerProps: headerNowrapProps,
      cellProps: tableCellProps,
    },
    {
      title: t("luca-guide.campaigns.detail.ads-table.columns.trend"),
      key: "trend",
      sortable: true,
      headerProps: headerNowrapProps,
      cellProps: tableCellProps,
    },
    {
      title: t("luca-guide.campaigns.detail.ads-table.columns.diagnosis"),
      key: "diagnosed",
      sortable: true,
      align: "center" as const,
      headerProps: headerNowrapProps,
      cellProps: tableCellProps,
    },
  ];
});

function trendLabel(trend: LucaGuideAdTrend) {
  const key = `luca-guide.campaigns.detail.ads-table.trends.${trend}`;
  return te(key) ? t(key) : trend;
}

function trendIcon(trend: LucaGuideAdTrend) {
  switch (trend) {
    case "rise":
      return "tabler:trending-up";
    case "fall":
      return "tabler:trending-down";
    case "new":
      return "tabler:file-text";
    default:
      return "tabler:minus";
  }
}

function trendClass(trend: LucaGuideAdTrend) {
  switch (trend) {
    case "rise":
      return "tw:text-success";
    case "fall":
      return "tw:text-error";
    case "new":
      return "tw:text-info";
    default:
      return "tw:text-secondary-text";
  }
}

function openAd(ad: LucaGuideCampaignAdsTableAd) {
  router.push({
    name: "LucaGuideCampaignAd",
    params: {
      brandId: route.params.brandId,
      campaignId: props.campaignId,
      adId: ad.ad_external_id,
    },
  });
}
</script>

<template>
  <VDataTable
    :items="ads"
    :headers="tableHeaders"
    v-model:sort-by="sortBy"
    :loading="loading"
    :items-per-page="-1"
    item-value="ad_external_id"
    hide-default-footer
    class="tw:cursor-pointer tw:text-xs"
    @click:row="(_event, { item }) => openAd(item)"
  >
    <template v-if="$slots.top" #top>
      <slot name="top" />
    </template>

    <template #item.state="{ item }">
      <LucaGuideAdClassificationChip :state="item.state" />
    </template>

    <template #item.ad_name="{ item }">
      <div class="tw:flex tw:flex-col" :title="item.ad_external_id">
        <span class="tw:font-medium tw:text-primary-text">
          {{ item.ad_name || "—" }}
        </span>
        <!-- HLG-153: show the ad set so duplicate ad names (e.g. 8 ads called
             "T1-V3") are distinguishable; the ad ID is on hover (title). -->
        <span
          v-if="item.ad_set_name"
          class="tw:text-[11px] tw:text-secondary-text"
        >
          {{ item.ad_set_name }}
        </span>
      </div>
    </template>

    <template
      v-for="(kpi, index) in kpis"
      :key="kpi.key"
      #[`item.kpi_${index}`]="{ item }"
    >
      <span
        class="tw:font-bold"
        :class="getLucaGuideKpiValueClass(item.values[index]?.good)"
      >
        {{
          formatLucaGuideKpiValue(
            item.values[index]?.value,
            kpi.format,
            locale,
            currency,
          )
        }}
      </span>
    </template>

    <template #item.spend="{ item }">
      {{ formatCurrencyValue(item.spend, locale, currency) }}
    </template>

    <template #item.trend="{ item }">
      <span
        class="tw:flex tw:items-center tw:gap-1 tw:font-semibold"
        :class="trendClass(item.trend)"
      >
        <Icon :icon="trendIcon(item.trend)" class="tw:text-[16px]" />
        <span>{{ trendLabel(item.trend) }}</span>
      </span>
    </template>

    <template #item.diagnosed="{ item }">
      <span
        class="tw:font-bold"
        :class="item.diagnosed ? 'tw:text-success' : 'tw:text-error'"
      >
        {{ item.diagnosed ? $t("global.yes") : $t("global.no") }}
      </span>
    </template>

    <template #no-data>
      <p class="tw:py-8 tw:text-center tw:text-secondary-text">
        <slot name="empty">
          {{ $t("luca-guide.campaigns.detail.ads-table.empty") }}
        </slot>
      </p>
    </template>
  </VDataTable>
</template>
