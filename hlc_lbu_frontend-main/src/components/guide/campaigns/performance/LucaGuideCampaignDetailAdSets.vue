<script setup lang="ts">
import type {
  LucaGuideCampaignAdsTable,
  LucaGuideCampaignAdsTableAd,
} from "@/services/guide/LucaGuideCampaignsApi";
import LucaGuideCampaignsApi from "@/services/guide/LucaGuideCampaignsApi";
import { CLASSIFICATION_THRESHOLDS } from "@/constants/guide/classification-thresholds";
import { LUCA_GUIDE_ENTIRE_PERIOD_DAYS } from "@/constants/guide/timeframe";

const UNGROUPED_AD_SET_KEY = "";
const INSUFFICIENT_DATA_KEY = "insufficient-data";

const STATE_DOT_CLASS: Record<string, string> = {
  success: "tw:bg-success",
  info: "tw:bg-info",
  warning: "tw:bg-warning",
  error: "tw:bg-error",
  secondary: "tw:bg-gray-400",
};

type AdSetStateCount = {
  key: string;
  color: string;
  count: number;
};

type AdSetGroup = {
  name: string;
  ads: LucaGuideCampaignAdsTableAd[];
  adCount: number;
  spend: number;
  primaryKpiValue: number | undefined;
  primaryKpiGood: boolean | undefined;
  stateCounts: AdSetStateCount[];
};

const props = defineProps<{
  campaignId: string;
  currency?: string;
}>();

const { t, te, locale } = useI18n();

const isLoading = ref(false);
const adsTable = ref<LucaGuideCampaignAdsTable>({
  kpis: [],
  ads: [],
  ad_sets: [],
  totals: { ad_count: 0, spend: 0, values: [] },
});

async function loadAdsTable() {
  isLoading.value = true;

  try {
    adsTable.value = await LucaGuideCampaignsApi.getAdsTable(
      props.campaignId,
      LUCA_GUIDE_ENTIRE_PERIOD_DAYS,
    );
  } catch (error) {
    console.error("Failed to load ad sets ads table:", error);
    throw error;
  } finally {
    isLoading.value = false;
  }
}

await loadAdsTable();

const primaryKpi = computed(() => adsTable.value.kpis[0]);

const primaryKpiLabel = computed(() => {
  const kpi = primaryKpi.value;
  if (!kpi) {
    return undefined;
  }

  const key = `luca-guide.kpis.${kpi.key}.short`;
  return te(key) ? t(key) : kpi.name;
});

function stateCountsFor(ads: LucaGuideCampaignAdsTableAd[]): AdSetStateCount[] {
  const classified = CLASSIFICATION_THRESHOLDS.flatMap((entry) => {
    const count = ads.filter((ad) => ad.state === entry.key).length;
    if (count === 0) {
      return [];
    }

    return [
      {
        key: entry.key,
        color: entry.color,
        count,
      },
    ];
  });

  const insufficientCount = ads.filter(
    (ad) => ad.state === INSUFFICIENT_DATA_KEY,
  ).length;

  if (insufficientCount === 0) {
    return classified;
  }

  return [
    ...classified,
    {
      key: INSUFFICIENT_DATA_KEY,
      color: "secondary",
      count: insufficientCount,
    },
  ];
}

const adSets = computed((): AdSetGroup[] => {
  const adsBySet = new Map<string, LucaGuideCampaignAdsTableAd[]>();

  for (const ad of adsTable.value.ads) {
    const name = ad.ad_set_name?.trim() || UNGROUPED_AD_SET_KEY;
    const ads = adsBySet.get(name);

    if (ads) {
      ads.push(ad);
    } else {
      adsBySet.set(name, [ad]);
    }
  }

  return adsTable.value.ad_sets.map((adSet) => {
    const name = adSet.ad_set_name?.trim() || UNGROUPED_AD_SET_KEY;
    const ads = adsBySet.get(name) ?? [];
    const primaryValue = adSet.values[0];

    return {
      name:
        name === UNGROUPED_AD_SET_KEY
          ? t("luca-guide.campaigns.detail.ad-sets.ungrouped")
          : name,
      ads,
      adCount: adSet.ad_count,
      spend: adSet.spend,
      primaryKpiValue: primaryValue?.value ?? undefined,
      primaryKpiGood: primaryValue?.good ?? undefined,
      stateCounts: stateCountsFor(ads),
    };
  });
});
</script>

<template>
  <div>
    <h2 class="tw:mb-2.5 tw:text-lg tw:font-bold">
      {{ $t("luca-guide.campaigns.detail.ad-sets.title") }}
    </h2>

    <!-- Loading state -->
    <CardBase
      v-if="isLoading && adSets.length === 0"
      borderRadius="lg"
      class="tw:overflow-hidden"
    >
      <LucaGuideCampaignDetailAdsDataTable
        :campaignId="campaignId"
        :ads="[]"
        :kpis="adsTable.kpis"
        :currency="currency"
        loading
      />
    </CardBase>

    <!-- Empty state -->
    <p
      v-else-if="adSets.length === 0"
      class="tw:py-8 tw:text-center tw:text-secondary-text"
    >
      {{ $t("luca-guide.campaigns.detail.ad-sets.empty") }}
    </p>

    <!-- Content -->
    <AccordionList v-else variant="card">
      <Accordion
        v-for="adSet in adSets"
        :key="adSet.name"
        titleClass="tw:w-full tw:font-normal"
        noContentPadding
      >
        <template #title>
          <span
            class="tw:flex tw:w-full tw:flex-col tw:gap-3 tw:sm:flex-row tw:sm:items-center tw:sm:gap-6"
          >
            <span class="tw:min-w-0 tw:grow tw:text-left">
              <span class="tw:block tw:text-lg tw:font-bold">
                {{ adSet.name }}
              </span>

              <span
                class="tw:mt-2 tw:flex tw:flex-wrap tw:items-center tw:gap-3 tw:text-sm tw:text-secondary-text"
              >
                <span>
                  {{
                    $t("luca-guide.campaigns.detail.ad-sets.ad-count", {
                      count: adSet.adCount,
                    })
                  }}
                </span>

                <span
                  v-for="state in adSet.stateCounts"
                  :key="state.key"
                  class="tw:inline-flex tw:items-center tw:gap-1"
                >
                  <span
                    class="tw:size-3.5 tw:rounded-full"
                    :class="STATE_DOT_CLASS[state.color] ?? 'tw:bg-gray-400'"
                  />

                  <span>{{ state.count }}</span>
                </span>
              </span>
            </span>

            <span class="tw:text-left tw:sm:text-right">
              <span class="tw:block tw:text-sm tw:text-secondary-text">
                {{ $t("luca-guide.campaigns.detail.ads-table.columns.spend") }}
              </span>

              <span class="tw:font-bold">
                {{ formatCurrencyValue(adSet.spend, locale, currency) }}
              </span>
            </span>

            <span v-if="primaryKpi" class="tw:text-left tw:sm:text-right">
              <span class="tw:block tw:text-sm tw:text-secondary-text">
                {{ primaryKpiLabel }}
              </span>

              <span
                class="tw:font-bold"
                :class="getLucaGuideKpiValueClass(adSet.primaryKpiGood)"
              >
                {{
                  formatLucaGuideKpiValue(
                    adSet.primaryKpiValue,
                    primaryKpi.format,
                    locale,
                    currency,
                  )
                }}
              </span>
            </span>
          </span>
        </template>

        <LucaGuideCampaignDetailAdsDataTable
          :campaignId="campaignId"
          :ads="adSet.ads"
          :kpis="adsTable.kpis"
          :currency="currency"
          :loading="isLoading"
        />
      </Accordion>
    </AccordionList>
  </div>
</template>
